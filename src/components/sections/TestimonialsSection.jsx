import React, { useEffect, useState } from 'react';
import { FaQuoteLeft, FaChevronLeft, FaChevronRight, FaStar } from 'react-icons/fa';

const testimonials = [
  {
    quote: "Complytics has transformed how we manage our security compliance. What used to take weeks now takes days, and our team can focus on strategic priorities.",
    author: "Sarah Johnson",
    title: "CISO, HealthTech Systems",
    rating: 5
  },
  {
    quote: "The Azure AD compliance automation has been a game-changer for our organization. We've reduced our security vulnerabilities by 75% in just three months.",
    author: "Michael Chen",
    title: "Security Director, FinanceCore",
    rating: 5
  },
  {
    quote: "The compliance chatbot has become our team's go-to resource. It's like having a compliance expert available 24/7 to answer our questions.",
    author: "Emily Rodriguez",
    title: "Compliance Manager, RetailGlobal",
    rating: 4
  },
  {
    quote: "We passed our SOC 2 audit with flying colors thanks to Complytics. The centralized knowledge base made document collection effortless.",
    author: "David Wilson",
    title: "CTO, SaaSPlatform Inc.",
    rating: 5
  }
];

const TestimonialsSection = () => {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  const handlePrev = () => {
    if (isAnimating) return;
    
    setIsAnimating(true);
    setActiveIndex((prev) => (prev === 0 ? testimonials.length - 1 : prev - 1));
    
    setTimeout(() => {
      setIsAnimating(false);
    }, 500);
  };

  const handleNext = () => {
    if (isAnimating) return;
    
    setIsAnimating(true);
    setActiveIndex((prev) => (prev === testimonials.length - 1 ? 0 : prev + 1));
    
    setTimeout(() => {
      setIsAnimating(false);
    }, 500);
  };

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

    const revealElements = document.querySelectorAll('.reveal');
    revealElements.forEach(el => {
      // Set initial styles
      el.style.opacity = '1';
      el.style.transform = 'translateY(0)';
      el.style.transition = 'all 800ms ease';
      observer.observe(el);
    });

    return () => {
      revealElements.forEach(el => observer.unobserve(el));
    };
  }, []);

  return (
    <section id="testimonials" className="section relative overflow-hidden py-24">
      <div className="gradient-blur top-1/4 right-1/4 opacity-30"></div>
      
      <div className="text-center mb-16">
        <h2 className="section-title">What Our Clients Say</h2>
        <p className="section-subtitle mx-auto">
          Trusted by leading organizations worldwide to streamline their security compliance
        </p>
      </div>

      <div className="relative max-w-4xl mx-auto">
        <div className={`glass-card rounded-xl p-8 md:p-10 relative overflow-hidden ${isAnimating ? 'opacity-0' : 'opacity-100'} transition-opacity duration-500`}>
          <div className="absolute top-4 left-4 text-primary/20">
            <FaQuoteLeft size={40} />
          </div>
          
          <div className="relative">
            <p className="text-lg md:text-xl mb-8">{testimonials[activeIndex].quote}</p>
            
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-semibold">{testimonials[activeIndex].author}</h4>
                <p className="text-sm text-muted-foreground">{testimonials[activeIndex].title}</p>
              </div>
              
              <div className="flex gap-1">
                {[...Array(testimonials[activeIndex].rating)].map((_, i) => (
                  <FaStar key={i} className="text-yellow-400" />
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-center gap-4 mt-8">
          <button
            onClick={handlePrev}
            className="p-2 rounded-full bg-white dark:bg-gray-800 shadow-md hover:shadow-lg transition-shadow"
          >
            <FaChevronLeft className="text-primary" />
          </button>
          <button
            onClick={handleNext}
            className="p-2 rounded-full bg-white dark:bg-gray-800 shadow-md hover:shadow-lg transition-shadow"
          >
            <FaChevronRight className="text-primary" />
          </button>
        </div>
      </div>
    </section>
  );
};

export default TestimonialsSection;