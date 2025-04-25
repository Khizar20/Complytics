import React, { useEffect } from 'react';
import { FaShieldAlt, FaSearch, FaComments, FaDatabase, FaCheck } from 'react-icons/fa';

const features = [
  {
    icon: <FaShieldAlt className="text-2xl" />,
    title: 'Azure AD Security Compliance',
    description: 'Automatically monitor and enforce security policies across your Azure AD environment with real-time compliance checks and remediation.',
    benefits: ['Continuous monitoring', 'Automated remediation', 'Compliance reporting']
  },
  {
    icon: <FaSearch className="text-2xl" />,
    title: 'UI Testing',
    description: 'Comprehensive automated testing to ensure your user interfaces meet accessibility standards and security requirements.',
    benefits: ['Accessibility validation', 'Security testing', 'Regression prevention']
  },
  {
    icon: <FaComments className="text-2xl" />,
    title: 'Compliance Assistant Chatbot',
    description: 'AI-powered assistant that helps answer compliance questions and guides you through complex security requirements.',
    benefits: ['24/7 assistance', 'Contextual guidance', 'Learning capabilities']
  },
  {
    icon: <FaDatabase className="text-2xl" />,
    title: 'Centralized Knowledge Base',
    description: 'A single source of truth for all your compliance documentation, policies, and procedures across the organization.',
    benefits: ['Searchable repository', 'Version control', 'Role-based access']
  }
];

const FeaturesSection = () => {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('active');
            observer.unobserve(entry.target);
          }
        });
      },
      { 
        threshold: 0.1,
        rootMargin: '50px'
      }
    );

    const revealElements = document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scale');
    revealElements.forEach(el => {
      // Set initial styles
      el.style.opacity = '1';
      el.style.transform = el.classList.contains('reveal-left') ? 'translateX(0)' : 
                         el.classList.contains('reveal-right') ? 'translateX(0)' : 
                         el.classList.contains('reveal-scale') ? 'scale(1)' : 'translateY(0)';
      el.style.transition = 'all 800ms ease';
      observer.observe(el);
    });

    return () => {
      revealElements.forEach(el => observer.unobserve(el));
    };
  }, []);

  return (
    <section id="features" className="section relative overflow-hidden py-24">
      <div className="gradient-blur top-1/4 -left-1/4 opacity-50 animate-pulse-slow"></div>
      
      <div className="text-center mb-16">
        <h2 className="section-title">Powerful Features</h2>
        <p className="section-subtitle mx-auto">
          Comprehensive tools designed to simplify and automate your security compliance journey
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-12">
        {features.map((feature, index) => (
          <div 
            key={index} 
            className={`glass-card rounded-xl p-8 relative overflow-hidden group hover-card`}
            style={{ transitionDelay: `${0.1 * (index + 2)}s` }}
          >
            <div className="feature-icon-wrapper">
              {feature.icon}
            </div>
            
            <h3 className="text-xl font-semibold mb-4">{feature.title}</h3>
            <p className="text-muted-foreground mb-6">{feature.description}</p>
            
            <ul className="space-y-2">
              {feature.benefits.map((benefit, i) => (
                <li key={i} className="flex items-center gap-2">
                  <FaCheck className="text-primary" />
                  <span>{benefit}</span>
                </li>
              ))}
            </ul>
            
            <div className="absolute -bottom-10 -right-10 w-32 h-32 bg-primary/5 rounded-full opacity-30 group-hover:opacity-100 transition-opacity duration-300"></div>
            <div className="absolute top-0 right-0 w-full h-1 bg-gradient-to-r from-transparent via-primary/30 to-transparent shimmer-effect opacity-0 group-hover:opacity-100"></div>
          </div>
        ))}
      </div>
      
      <div className="mt-24 bg-secondary/50 rounded-xl p-8 md:p-12 relative">
        <div className="max-w-3xl">
          <h3 className="text-2xl font-semibold mb-4">Why Choose Complytics?</h3>
          <p className="text-lg mb-6">
            Our platform reduces compliance workload by up to 80%, helping your team focus on innovation instead of repetitive security tasks.
          </p>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
            <div className="bg-white/50 backdrop-blur-sm rounded-lg p-6 hover-card animated-border">
              <div className="text-3xl font-bold text-primary mb-2 animate-count">85%</div>
              <p className="text-sm text-muted-foreground">Reduction in compliance-related incidents</p>
            </div>
            
            <div className="bg-white/50 backdrop-blur-sm rounded-lg p-6 hover-card animated-border" style={{ transitionDelay: '0.1s' }}>
              <div className="text-3xl font-bold text-primary mb-2 animate-count">60%</div>
              <p className="text-sm text-muted-foreground">Less time spent on manual security checks</p>
            </div>
            
            <div className="bg-white/50 backdrop-blur-sm rounded-lg p-6 hover-card animated-border" style={{ transitionDelay: '0.2s' }}>
              <div className="text-3xl font-bold text-primary mb-2 animate-count">90%</div>
              <p className="text-sm text-muted-foreground">Faster security compliance reporting</p>
            </div>
          </div>
        </div>
        
        <div className="hidden md:block absolute -top-12 -right-12 w-40 h-40 bg-primary/10 rounded-full blur-xl animate-pulse-slow"></div>
      </div>
    </section>
  );
};

export default FeaturesSection;