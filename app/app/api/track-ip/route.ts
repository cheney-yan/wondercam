import { NextRequest, NextResponse } from 'next/server';
import { createServerClient } from '@supabase/ssr';

/**
 * Cloudflare / Proxy IP extraction strategy
 * Priority:
 *  1. true-client-ip (some proxies / Cloudflare Enterprise)
 *  2. cf-connecting-ip (Cloudflare standard)
 *  3. x-real-ip
 *  4. First public IP in x-forwarded-for chain
 *  5. fly-client-ip / forwarded (RFC 7239)
 *  6. Fallback request.ip (may be undefined in some runtimes)
 *
 * We now also record private / localhost IPs in development for debugging.
 */

const ipCandidateHeaders = [
  'true-client-ip',
  'cf-connecting-ip',
  'x-real-ip',
  'fly-client-ip'
];

const IP_REGEX =
  /^(([0-9]{1,3}\.){3}[0-9]{1,3}|(([a-fA-F0-9]{0,4}:){2,7}[a-fA-F0-9]{0,4}))$/;

function normalizeIp(raw: string): string | null {
  if (!raw) return null;
  let v = raw.trim().replace(/^\[|\]$/g, ''); // strip brackets for IPv6
  // Remove port if present (IPv4:port or [IPv6]:port patterns)
  v = v.replace(/^(.*?)(:\d+)?$/, '$1');
  if (IP_REGEX.test(v)) return v;
  return null;
}

function isLoopback(ip: string) {
  const lower = ip.toLowerCase();
  return (
    lower === '127.0.0.1' ||
    lower === '::1'
  );
}

function isPrivate(ip: string) {
  // Simple RFC1918 / unique-local detection
  if (ip.includes(':')) {
    // IPv6 unique local fc00::/7
    return /^fc|^fd/i.test(ip);
  }
  const parts = ip.split('.').map(p => parseInt(p, 10));
  if (parts.length !== 4) return false;
  return (
    parts[0] === 10 ||
    (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) ||
    (parts[0] === 192 && parts[1] === 168)
  );
}

/**
 * POST /api/track-ip
 * Returns JSON { success, ip, source, reason? }
 */
export async function POST(request: NextRequest) {
  try {
    const headerMap: Record<string, string | null> = {};
    ipCandidateHeaders.forEach(h => {
      headerMap[h] = request.headers.get(h);
    });
    const xffRaw = request.headers.get('x-forwarded-for') || '';
    const forwarded = request.headers.get('forwarded') || '';

    const xffChain = xffRaw
      .split(',')
      .map(s => s.trim())
      .filter(Boolean)
      .map(normalizeIp)
      .filter(Boolean) as string[];

    const forwardedExtracted: string[] = [];
    if (forwarded) {
      forwarded.split(',').forEach(part => {
        const m = /for=([^;]+)/i.exec(part);
        if (m) {
          const cleaned = normalizeIp(m[1].replace(/^"|"$/g, ''));
          if (cleaned) forwardedExtracted.push(cleaned);
        }
      });
    }

    // Ordered candidate list
    const candidates: { ip: string; source: string }[] = [];

    for (const h of ipCandidateHeaders) {
      const val = headerMap[h];
      const norm = val ? normalizeIp(val) : null;
      if (norm) candidates.push({ ip: norm, source: h });
    }

    xffChain.forEach(ip => candidates.push({ ip, source: 'x-forwarded-for' }));
    forwardedExtracted.forEach(ip => candidates.push({ ip, source: 'forwarded' }));

    // (Fallback request.ip removed – not typed on NextRequest and was causing TS error)

    let chosen: { ip: string; source: string } | null = null;

    for (const c of candidates) {
      /**
       * Selection policy:
       * - Always skip loopback (127.0.0.1 / ::1) in production.
       * - Accept private RFC1918 / ULA addresses (10.x, 172.16/12, 192.168.x, fc00::/7)
       *   because when sitting behind Cloudflare or another reverse proxy, the
       *   application may only see an internal egress IP unless special headers are
       *   enabled. Rejecting these caused NULL storage.
       * - In development also accept loopback so local testing records something.
       */
      if (process.env.NODE_ENV === 'production') {
        if (isLoopback(c.ip)) {
          continue;
        }
      }
      chosen = c;
      break;
    }

    // If still no choice and we had only loopback then allow loopback (better than null)
    if (!chosen && candidates.length > 0) {
      chosen = candidates[0];
    }

    // If nothing left choose first even if private (to at least have *something*)
    if (!chosen && candidates.length > 0) {
      chosen = candidates[0];
    }

    const ipToStore = chosen?.ip || null;

    // Build Supabase server client
    let response = NextResponse.next();
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_OR_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return request.cookies.getAll();
          },
          setAll(cookiesToSet) {
            cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
            response = NextResponse.next({ request });
            cookiesToSet.forEach(({ name, value, options }) =>
              response.cookies.set(name, value, options)
            );
          },
        },
      }
    );

    const { data: { user }, error: userError } = await supabase.auth.getUser();
    if (userError || !user) {
      return NextResponse.json({
        success: false,
        ip: ipToStore,
        source: chosen?.source || null,
        reason: 'No authenticated/anonymous user session'
      }, { status: 200 });
    }

    // Store even if null (function will set NULL)
    const { error: rpcError } = await supabase.rpc('set_last_login_ip', { p_ip: ipToStore });
    if (rpcError) {
      return NextResponse.json({
        success: false,
        ip: ipToStore,
        source: chosen?.source || null,
        error: rpcError.message
      }, { status: 500 });
    }

    if (process.env.NODE_ENV !== 'production') {
      // Emit debug info to server logs for troubleshooting
      console.log('[track-ip] candidates:', candidates);
      console.log('[track-ip] chosen:', chosen);
    }

    return NextResponse.json({
      success: true,
      ip: ipToStore,
      source: chosen?.source || null,
      private: ipToStore ? isPrivate(ipToStore) : null,
      loopback: ipToStore ? isLoopback(ipToStore) : null,
      raw: {
        xForwardedFor: xffRaw || null,
        forwarded: forwarded || null,
        headers: headerMap
      }
    }, { status: 200 });

  } catch (err: any) {
    return NextResponse.json(
      { success: false, error: err?.message ?? 'Unknown error' },
      { status: 500 }
    );
  }
}