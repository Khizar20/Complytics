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
    <section id="features" className="section relative overflow-hidden py-24 bg-blue-50/30">
      <div className="absolute top-1/4 -left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl opacity-50 animate-pulse-slow"></div>
      
      <div className="text-center mb-16 relative z-10">
        <h2 className="text-4xl md:text-5xl font-bold text-black mb-4">Powerful Features</h2>
        <p className="text-lg md:text-xl text-gray-600 max-w-3xl mx-auto">
          Comprehensive tools designed to simplify and automate your security compliance journey
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-12 relative z-10">
        {features.map((feature, index) => (
          <div 
            key={index} 
            className={`bg-white border-2 border-black rounded-xl p-8 relative overflow-hidden group hover:shadow-2xl transition-all duration-300 hover:-translate-y-2`}
            style={{ transitionDelay: `${0.1 * (index + 2)}s` }}
          >
            <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mb-6 text-white shadow-lg">
              {feature.icon}
            </div>
            
            <h3 className="text-2xl font-bold text-black mb-4">{feature.title}</h3>
            <p className="text-gray-600 mb-6 leading-relaxed">{feature.description}</p>
            
            <ul className="space-y-3">
              {feature.benefits.map((benefit, i) => (
                <li key={i} className="flex items-center gap-3">
                  <FaCheck className="text-blue-600 text-lg" />
                  <span className="text-gray-700 font-medium">{benefit}</span>
                </li>
              ))}
            </ul>
            
            <div className="absolute -bottom-10 -right-10 w-32 h-32 bg-blue-500/10 rounded-full opacity-30 group-hover:opacity-50 transition-opacity duration-300"></div>
            <div className="absolute top-0 right-0 w-full h-1 bg-gradient-to-r from-transparent via-blue-600 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          </div>
        ))}
      </div>
      
      <div className="mt-24 bg-gradient-to-br from-white to-blue-50/60 border-2 border-black rounded-xl p-8 md:p-12 relative shadow-lg">
        <div className="max-w-3xl">
          <h3 className="text-3xl font-bold text-black mb-4">Why Choose Complytics?</h3>
          <p className="text-lg text-gray-700 mb-8 leading-relaxed">
            Our platform reduces compliance workload by up to 80%, helping your team focus on innovation instead of repetitive security tasks.
          </p>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
            <div className="bg-white border-2 border-black rounded-lg p-6 hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
              <div className="text-4xl font-bold text-blue-600 mb-2">85%</div>
              <p className="text-sm text-gray-600 font-medium">Reduction in compliance-related incidents</p>
            </div>
            
            <div className="bg-white border-2 border-black rounded-lg p-6 hover:shadow-xl transition-all duration-300 hover:-translate-y-1" style={{ transitionDelay: '0.1s' }}>
              <div className="text-4xl font-bold text-blue-600 mb-2">60%</div>
              <p className="text-sm text-gray-600 font-medium">Less time spent on manual security checks</p>
            </div>
            
            <div className="bg-white border-2 border-black rounded-lg p-6 hover:shadow-xl transition-all duration-300 hover:-translate-y-1" style={{ transitionDelay: '0.2s' }}>
              <div className="text-4xl font-bold text-blue-600 mb-2">90%</div>
              <p className="text-sm text-gray-600 font-medium">Faster security compliance reporting</p>
            </div>
          </div>
        </div>
        
        <div className="hidden md:block absolute -top-12 -right-12 w-40 h-40 bg-blue-500/20 rounded-full blur-xl animate-pulse-slow"></div>
      </div>
    </section>
  );
};

export default FeaturesSection;