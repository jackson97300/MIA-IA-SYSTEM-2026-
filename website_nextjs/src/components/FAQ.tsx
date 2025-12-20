'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, HelpCircle } from 'lucide-react'

const faqs = [
  {
    question: "Qu'est-ce que MIA IA SYSTEM ?",
    answer: "MIA est un système de trading algorithmique qui analyse les marchés futures (ES, NQ, RTY) 24h/24 et génère des signaux de trading basés sur une stratégie propriétaire développée pendant plus de 10 ans.",
  },
  {
    question: 'Faut-il des connaissances en trading ?',
    answer: "Une connaissance de base des marchés est recommandée. MIA est un outil d'aide à la décision, pas un système de gains garantis. Comprendre les risques du trading est essentiel.",
  },
  {
    question: 'Comment sont générés les signaux ?',
    answer: "MIA utilise une stratégie propriétaire combinant analyse technique avancée et intelligence artificielle pour identifier les meilleures opportunités de trading.",
  },
  {
    question: "C'est gratuit ?",
    answer: "Oui ! L'accès au dashboard MIA est actuellement 100% gratuit. Des offres premium avec des fonctionnalités avancées seront disponibles prochainement.",
  },
  {
    question: "Puis-je perdre de l'argent ?",
    answer: "Oui. Le trading comporte des risques de perte en capital. Les performances passées ne garantissent pas les résultats futurs. N'investissez jamais plus que ce que vous pouvez vous permettre de perdre.",
  },
  {
    question: 'Comment accéder au dashboard ?',
    answer: "Créez un compte gratuit ou connectez-vous avec Google, puis cliquez sur 'Accéder au Dashboard'. Vous serez redirigé vers l'interface de MIA.",
  },
]

function FAQItem({ faq, isOpen, onClick }: { 
  faq: typeof faqs[0]
  isOpen: boolean
  onClick: () => void 
}) {
  return (
    <div className="faq-item">
      <button
        className="faq-question"
        onClick={onClick}
        aria-expanded={isOpen}
      >
        <span className="flex items-center gap-3">
          <HelpCircle className="w-5 h-5 text-mia-cyan flex-shrink-0" />
          {faq.question}
        </span>
        <ChevronDown
          className={`w-5 h-5 text-light-400 transition-transform duration-300 
                    ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="faq-answer">
              {faq.answer}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  return (
    <section id="faq" className="section relative">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-dark-200/30 to-transparent" />
      
      <div className="container-custom relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="section-title">
            <span className="text-gradient">Questions Fréquentes</span>
          </h2>
          <p className="section-subtitle">
            Tout ce que vous devez savoir sur MIA IA SYSTEM
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="max-w-3xl mx-auto"
        >
          {faqs.map((faq, index) => (
            <FAQItem
              key={index}
              faq={faq}
              isOpen={openIndex === index}
              onClick={() => setOpenIndex(openIndex === index ? null : index)}
            />
          ))}
        </motion.div>

        {/* Contact prompt */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.5 }}
          className="text-center mt-12"
        >
          <p className="text-light-400 mb-4">
            Vous ne trouvez pas la réponse que vous cherchez ?
          </p>
          <a href="#contact" className="btn-secondary">
            Contactez-nous
          </a>
        </motion.div>
      </div>
    </section>
  )
}
