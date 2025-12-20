'use client'

import { motion } from 'framer-motion'
import { Check, Sparkles } from 'lucide-react'

const plans = [
  {
    name: 'Gratuit',
    price: '0€',
    period: '/mois',
    badge: 'ACTUEL',
    badgeColor: 'bg-mia-cyan',
    highlight: true,
    features: [
      'Accès au dashboard',
      'Signaux en temps réel',
      'Alertes Discord',
      'Statistiques complètes',
      'Support communautaire',
    ],
    cta: 'Commencer gratuitement',
    ctaStyle: 'btn-primary',
  },
  {
    name: 'Premium',
    price: '---',
    period: '',
    badge: 'BIENTÔT',
    badgeColor: 'bg-accent-warning',
    highlight: false,
    features: [
      'Tout du plan Gratuit',
      'Fonctionnalités avancées',
      'Support prioritaire',
      'Accès API',
      'Et plus encore...',
    ],
    cta: 'Bientôt disponible',
    ctaStyle: 'btn-secondary opacity-50 cursor-not-allowed',
    disabled: true,
  },
]

export default function Pricing() {
  return (
    <section id="pricing" className="section relative">
      <div className="container-custom">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="section-title">
            <span className="text-gradient">Tarifs</span>
          </h2>
          <p className="section-subtitle">
            Commencez gratuitement, évoluez selon vos besoins
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {plans.map((plan, index) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.2 }}
              className={`pricing-card ${plan.highlight ? 'pricing-card-highlight' : ''}`}
            >
              {/* Badge */}
              <div className={`absolute -top-3 left-1/2 -translate-x-1/2 
                            ${plan.badgeColor} text-dark text-xs font-bold 
                            px-4 py-1 rounded-full`}>
                {plan.badge}
              </div>

              {/* Plan name */}
              <h3 className="text-2xl font-bold text-white mt-4 mb-2">
                {plan.name}
              </h3>

              {/* Price */}
              <div className="mb-6">
                <span className="text-5xl font-bold text-mia-cyan">{plan.price}</span>
                <span className="text-light-400">{plan.period}</span>
              </div>

              {/* Features */}
              <ul className="space-y-4 mb-8 text-left">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-3">
                    <Check className="w-5 h-5 text-mia-cyan flex-shrink-0" />
                    <span className="text-light-300">{feature}</span>
                  </li>
                ))}
              </ul>

              {/* CTA Button */}
              <button
                className={`${plan.ctaStyle} w-full`}
                disabled={plan.disabled}
              >
                {plan.highlight && <Sparkles className="w-5 h-5" />}
                {plan.cta}
              </button>
            </motion.div>
          ))}
        </div>

        {/* Bottom note */}
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.5 }}
          className="text-center text-light-500 text-sm mt-12"
        >
          Pas de carte bancaire requise • Annulez à tout moment
        </motion.p>
      </div>
    </section>
  )
}
