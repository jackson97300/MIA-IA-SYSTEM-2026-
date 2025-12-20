import type { Metadata } from 'next'
import '../styles/globals.css'

export const metadata: Metadata = {
  title: 'MIA IA SYSTEM - Intelligence Artificielle pour le Trading Futures',
  description: 'Robot de trading algorithmique qui analyse les marchés ES, NQ, RTY 24h/24. Prenez de meilleures décisions, sans stress, sans émotions.',
  keywords: 'trading, IA, intelligence artificielle, futures, ES, NQ, RTY, algorithme, bot trading, MIA',
  authors: [{ name: 'MIA IA SYSTEM' }],
  openGraph: {
    title: 'MIA IA SYSTEM - Trading Intelligent',
    description: 'Votre Assistant Intelligent de Trading',
    url: 'https://mia-ia-system.com',
    siteName: 'MIA IA SYSTEM',
    locale: 'fr_FR',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'MIA IA SYSTEM',
    description: 'Intelligence Artificielle pour le Trading Futures',
  },
  robots: {
    index: true,
    follow: true,
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="fr" className="scroll-smooth">
      <head>
        <link rel="icon" href="/images/logo-dark.jpg" />
        <link rel="apple-touch-icon" href="/images/logo-dark.jpg" />
      </head>
      <body className="bg-dark text-white overflow-x-hidden">
        {children}
      </body>
    </html>
  )
}
