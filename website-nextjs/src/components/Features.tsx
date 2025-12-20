'use client'

import { motion } from 'framer-motion'
import { 
  BarChart3, 
  Target, 
  Bot, 
  Smartphone, 
  Bell, 
  LineChart,
  GraduationCap,
  Calendar
} from 'lucide-react'

const features = [
  {
    icon: BarChart3,
    title: 'Analyse Temps Réel',
    description: 'Surveillance continue des marchés futures ES, NQ et RTY, 24h/24.',
    color: 'text-mia-cyan',
    bgColor: 'bg-mia-cyan/10',
  },
  {
    icon: Target,
    title: 'Signaux Précis',
    description: 'Entrées et sorties optimisées par intelligence artificielle.',
    color: 'text-accent-purple',
    bgColor: 'bg-accent-purple/10',
  },
  {
    icon: Bot,
    title: '100% Automatisé',
    description: 'Trading sans intervention manuelle, sans émotions, sans stress.',
    color: 'text-mia-gold',
    bgColor: 'bg-mia-gold/10',
  },
  {
    icon: Smartphone,
    title: 'Accessible Partout',
    description: "Dashboard accessible depuis n'importe quel appareil, où que vous soyez.",
    color: 'text-mia-cyan',
    bgColor: 'bg-mia-cyan/10',
  },
  {
    icon: Bell,
    title: 'Alertes Instantanées',
    description: 'Notifications Discord en temps réel pour chaque signal et trade.',
    color: 'text-accent-error',
    bgColor: 'bg-accent-error/10',
  },
  {
    icon: LineChart,
    title: 'Dashboard Live',
    description: 'Visualisez les performances, statistiques et trades en temps réel.',
    color: 'text-accent-purple',
    bgColor: 'bg-accent-purple/10',
  },
  {
    icon: GraduationCap,
    title: 'Éducation Trading',
    description: 'Ressources éducatives pour comprendre les marchés et améliorer vos compétences.',
    color: 'text-mia-gold',
    bgColor: 'bg-mia-gold/10',
  },
  {
    icon: Calendar,
    title: 'Calendrier Économique',
    description: 'Suivi des annonces économiques majeures qui impactent les marchés.',
    color: 'text-mia-cyan',
    bgColor: 'bg-mia-cyan/10',
  },
]

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: 'easeOut',
    },
  },
}

export default function Features() {
  return (
    <section id="features" className="section relative">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-dark-200/50 to-transparent" />
      
      <div className="container-custom relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="section-title">
            <span className="text-gradient">Fonctionnalités</span>
          </h2>
          <p className="section-subtitle">
            Tout ce dont vous avez besoin pour un trading intelligent
          </p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-100px' }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
        >
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              variants={itemVariants}
              className="feature-card group"
            >
              {/* Top accent line */}
              <div className={`absolute top-0 left-0 right-0 h-1 ${feature.bgColor} 
                            opacity-0 group-hover:opacity-100 transition-opacity rounded-t-2xl`} />
              
              {/* Icon */}
              <div className={`w-16 h-16 ${feature.bgColor} rounded-xl 
                            flex items-center justify-center mx-auto mb-5
                            group-hover:scale-110 transition-transform duration-300`}>
                <feature.icon className={`w-8 h-8 ${feature.color}`} />
              </div>
              
              {/* Title */}
              <h3 className="text-lg font-semibold text-white mb-3 group-hover:text-mia-cyan transition-colors">
                {feature.title}
              </h3>
              
              {/* Description */}
              <p className="text-light-400 text-sm leading-relaxed">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}
