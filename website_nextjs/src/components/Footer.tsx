'use client'

import Image from 'next/image'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { AlertTriangle } from 'lucide-react'

const footerLinks = {
  product: [
    { label: 'Accueil', href: '#hero' },
    { label: 'Services', href: '#features' },
    { label: 'Tarifs', href: '#pricing' },
    { label: 'FAQ', href: '#faq' },
  ],
  legal: [
    { label: 'CGU', href: '/terms' },
    { label: 'Confidentialité', href: '/privacy' },
    { label: 'Mentions légales', href: '/legal' },
    { label: 'Risques', href: '/risk' },
  ],
}

export default function Footer() {
  const currentYear = new Date().getFullYear()

  const handleNavClick = (href: string) => {
    if (href.startsWith('#')) {
      const element = document.querySelector(href)
      if (element) {
        const offset = 80
        const elementPosition = element.getBoundingClientRect().top
        const offsetPosition = elementPosition + window.pageYOffset - offset
        window.scrollTo({ top: offsetPosition, behavior: 'smooth' })
      }
    }
  }

  return (
    <footer className="relative border-t border-white/10 bg-dark-100">
      <div className="container-custom py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12">
          {/* Brand */}
          <div className="lg:col-span-1">
            <div className="flex items-center gap-3 mb-4">
              <div className="relative w-10 h-10">
                <Image
                  src="/images/logo-dark.jpg"
                  alt="MIA IA SYSTEM"
                  fill
                  className="rounded-full object-cover border border-mia-gold/50"
                />
              </div>
              <span className="text-lg font-bold text-white">MIA IA SYSTEM</span>
            </div>
            <p className="text-light-400 text-sm leading-relaxed">
              Intelligence Artificielle pour le Trading Futures.
              Analysez les marchés 24h/24 sans stress et sans émotions.
            </p>
          </div>

          {/* Product Links */}
          <div>
            <h4 className="text-white font-semibold mb-4">Liens</h4>
            <ul className="space-y-3">
              {footerLinks.product.map((link) => (
                <li key={link.label}>
                  <button
                    onClick={() => handleNavClick(link.href)}
                    className="text-light-400 hover:text-mia-cyan transition-colors text-sm"
                  >
                    {link.label}
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal Links */}
          <div>
            <h4 className="text-white font-semibold mb-4">Légal</h4>
            <ul className="space-y-3">
              {footerLinks.legal.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    className="text-light-400 hover:text-mia-cyan transition-colors text-sm"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h4 className="text-white font-semibold mb-4">Contact</h4>
            <a
              href="mailto:contact@mia-ia-system.com"
              className="text-light-400 hover:text-mia-cyan transition-colors text-sm flex items-center gap-2"
            >
              📧 contact@mia-ia-system.com
            </a>
          </div>
        </div>

        {/* Bottom section */}
        <div className="mt-12 pt-8 border-t border-white/10">
          {/* Copyright */}
          <p className="text-center text-light-500 text-sm mb-6">
            © {currentYear} MIA IA SYSTEM. Tous droits réservés.
          </p>

          {/* Risk Warning */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="max-w-3xl mx-auto"
          >
            <div className="bg-accent-warning/10 border border-accent-warning/30
                          rounded-xl p-4 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-accent-warning flex-shrink-0 mt-0.5" />
              <p className="text-accent-warning text-xs leading-relaxed">
                <strong>Avertissement :</strong> Le trading comporte des risques de perte en capital.
                Les performances passées ne garantissent pas les résultats futurs.
                N'investissez jamais plus que ce que vous pouvez vous permettre de perdre.
                MIA IA SYSTEM est un outil d'aide à la décision et ne constitue pas un conseil en investissement.
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </footer>
  )
}
