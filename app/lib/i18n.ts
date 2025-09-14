import { SupportedLanguage } from '@/app/wondercam/page';

export const translations = {
  en: {
    // Upgrade Prompt
    outOfCreditsTitle: '🚫 Out of Credits',
    lowOnCreditsTitle: '⚠️ Running Low on Credits',
    upgradeAccountTitle: '⚡ Upgrade Your Account',
    creditsExhaustedMessage: "You've used all your daily credits. Create a free account to receive 50 credits every day.",
    lowCreditsMessage: (credits: number) => `You only have ${credits} credits left. Create a free account to receive 50 credits every day.`,
    manualUpgradeMessage: 'Create a free account to receive 50 credits every day.',
    whatYouGet: "✨ Benefit:",
    instantAccess: 'Receive 50 credits daily',
    createFreeAccount: 'Create Free Account',
    creatingAccount: 'Creating Account...',
    maybeLater: 'Maybe Later',
    freeAccountInfo: '🔒 100% free • No credit card required',
    
    // Compact Upgrade Prompt
    compactOutOfCredits: "Out of credits! Get 50 daily with a free account.",
    compactLowCredits: (credits: number) => `${credits} left. Get 50 daily with a free account.`,
    upgrade: 'Upgrade',
    later: 'Later',

    // Insufficient Credits Alert
    insufficientCredits: 'Insufficient credits. You need 2 credits to process a photo.',

    // Benefits (minimal — only what can be promised)
    benefits: [
      '50 credits daily'
    ]
  },
  zh: {
    // Upgrade Prompt
    outOfCreditsTitle: '🚫 信用点数不足',
    lowOnCreditsTitle: '⚠️ 信用点数即将用尽',
    upgradeAccountTitle: '⚡ 升级您的帐户',
    creditsExhaustedMessage: '您的每日信用点数已用完。创建免费帐户即可每天获得 50 个信用点数。',
    lowCreditsMessage: (credits: number) => `您只剩下 ${credits} 个信用点数。创建免费帐户即可每天获得 50 个信用点数。`,
    manualUpgradeMessage: '创建免费帐户即可每天获得 50 个信用点数。',
    whatYouGet: '✨ 益处：',
    instantAccess: '每天获得 50 个信用点数',
    createFreeAccount: '创建免费帐户',
    creatingAccount: '正在创建帐户...',
    maybeLater: '以后再说',
    freeAccountInfo: '🔒 100% 免费 • 无需信用卡',

    // Compact Upgrade Prompt
    compactOutOfCredits: '信用点数用完了！免费帐户每天 50 个。',
    compactLowCredits: (credits: number) => `剩余 ${credits} 个。免费帐户每天 50 个。`,
    upgrade: '升级',
    later: '以后',

    // Insufficient Credits Alert
    insufficientCredits: '信用点数不足。处理照片需要 2 个信用点数。',

    // Benefits
    benefits: [
      '每天 50 个信用点数'
    ]
  },
  es: {
    // Upgrade Prompt
    outOfCreditsTitle: '🚫 Sin créditos',
    lowOnCreditsTitle: '⚠️ Pocos créditos',
    upgradeAccountTitle: '⚡ Mejora tu cuenta',
    creditsExhaustedMessage: 'Has usado todos tus créditos diarios. Crea una cuenta gratuita para recibir 50 créditos cada día.',
    lowCreditsMessage: (credits: number) => `Solo te quedan ${credits} créditos. Crea una cuenta gratuita para recibir 50 créditos cada día.`,
    manualUpgradeMessage: 'Crea una cuenta gratuita para recibir 50 créditos cada día.',
    whatYouGet: '✨ Beneficio:',
    instantAccess: 'Recibe 50 créditos diarios',
    createFreeAccount: 'Crear cuenta gratuita',
    creatingAccount: 'Creando cuenta...',
    maybeLater: 'Quizás más tarde',
    freeAccountInfo: '🔒 100% gratis • Sin tarjeta',

    // Compact Upgrade Prompt
    compactOutOfCredits: '¡Sin créditos! Consigue 50 diarios con una cuenta gratuita.',
    compactLowCredits: (credits: number) => `Quedan ${credits}. Consigue 50 diarios con una cuenta gratuita.`,
    upgrade: 'Mejorar',
    later: 'Después',

    // Insufficient Credits Alert
    insufficientCredits: 'Créditos insuficientes. Necesitas 2 para procesar una foto.',

    // Benefits
    benefits: [
      '50 créditos diarios'
    ]
  },
  fr: {
    // Upgrade Prompt
    outOfCreditsTitle: '🚫 Crédits épuisés',
    lowOnCreditsTitle: '⚠️ Crédits faibles',
    upgradeAccountTitle: '⚡ Améliorez votre compte',
    creditsExhaustedMessage: 'Vous avez utilisé tous vos crédits quotidiens. Créez un compte gratuit pour recevoir 50 crédits chaque jour.',
    lowCreditsMessage: (credits: number) => `Il ne vous reste que ${credits} crédits. Créez un compte gratuit pour recevoir 50 crédits chaque jour.`,
    manualUpgradeMessage: 'Créez un compte gratuit pour recevoir 50 crédits chaque jour.',
    whatYouGet: '✨ Avantage :',
    instantAccess: 'Recevez 50 crédits par jour',
    createFreeAccount: 'Créer un compte gratuit',
    creatingAccount: 'Création...',
    maybeLater: 'Plus tard',
    freeAccountInfo: '🔒 100% gratuit • Aucune carte',

    // Compact Upgrade Prompt
    compactOutOfCredits: 'Plus de crédits ! 50 quotidiens avec un compte gratuit.',
    compactLowCredits: (credits: number) => `${credits} restants. 50/jour avec un compte gratuit.`,
    upgrade: 'Améliorer',
    later: 'Plus tard',

    // Insufficient Credits Alert
    insufficientCredits: 'Crédits insuffisants. 2 nécessaires pour traiter une photo.',

    // Benefits
    benefits: [
      '50 crédits par jour'
    ]
  },
  ja: {
    // Upgrade Prompt
    outOfCreditsTitle: '🚫 クレジットがありません',
    lowOnCreditsTitle: '⚠️ クレジット残量が少ない',
    upgradeAccountTitle: '⚡ アカウントをアップグレード',
    creditsExhaustedMessage: '毎日のクレジットを使い切りました。無料アカウントで毎日 50 クレジットを受け取れます。',
    lowCreditsMessage: (credits: number) => `残り ${credits} クレジットです。無料アカウントで毎日 50 クレジットを受け取れます。`,
    manualUpgradeMessage: '無料アカウントで毎日 50 クレジットを受け取れます。',
    whatYouGet: '✨ 利点：',
    instantAccess: '毎日 50 クレジット',
    createFreeAccount: '無料アカウント作成',
    creatingAccount: '作成中...',
    maybeLater: '後で',
    freeAccountInfo: '🔒 100% 無料 • カード不要',

    // Compact Upgrade Prompt
    compactOutOfCredits: 'クレジットがありません。無料アカウントで毎日50。',
    compactLowCredits: (credits: number) => `残り ${credits}。無料アカウントで毎日50。`,
    upgrade: 'アップグレード',
    later: '後で',

    // Insufficient Credits Alert
    insufficientCredits: 'クレジット不足です。写真の処理には 2 クレジット必要です。',

    // Benefits
    benefits: [
      '毎日 50 クレジット'
    ]
  }
};

export const getTranslations = (lang: SupportedLanguage) => translations[lang];