import { NextRequest, NextResponse } from 'next/server';
import { createServerClient } from '@supabase/ssr';

export async function POST(request: NextRequest) {
  try {
    const { amount = 2 } = await request.json().catch(() => ({ amount: 2 }));
    // Create a server-side Supabase client bound to cookies
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

    // Get current user (required to know which row to update)
    const { data: { user }, error: userError } = await supabase.auth.getUser();
    if (userError) {
      return NextResponse.json({ success: false, error: userError.message }, { status: 401 });
    }
    if (!user) {
      return NextResponse.json({ success: false, error: 'Not authenticated' }, { status: 401 });
    }

    // Call RPC on server (keeps function signature and permissions off the client)
    const { data, error } = await supabase.rpc('consume_credits', {
      p_user_id: user.id,
      p_amount: amount
    });

    if (error) {
      return NextResponse.json({ success: false, error: error.message }, { status: 400 });
    }

    return NextResponse.json(data ?? { success: true }, { status: 200 });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err?.message ?? 'Unknown error' }, { status: 500 });
  }
}