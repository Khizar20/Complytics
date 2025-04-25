import React, { useEffect, useRef } from 'react';
import { FaShieldAlt, FaCheckCircle, FaLock, FaArrowRight } from 'react-icons/fa';
import { Button } from "../ui/button.jsx";

const HeroSection = () => {
  const heroRef = useRef(null);

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

    if (heroRef.current) {
      const revealElements = heroRef.current.querySelectorAll('.reveal');
      revealElements.forEach(el => {
        // Set initial styles
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
        el.style.transition = 'all 800ms ease';
        observer.observe(el);
      });
    }

    return () => {
      if (heroRef.current) {
        const revealElements = heroRef.current.querySelectorAll('.reveal');
        revealElements.forEach(el => observer.unobserve(el));
      }
    };
  }, []);

  return (
    <section ref={heroRef} className="relative overflow-hidden pt-28 pb-16 md:pt-36 md:pb-24 bg-background">
      {/* Animated background elements */}
      <div className="gradient-blur top-0 left-1/3 animate-pulse-slow"></div>
      <div className="gradient-blur bottom-0 right-1/3 animate-pulse-slow" style={{ animationDelay: '2s' }}></div>
      
      {/* Decorative circles */}
      <div className="absolute top-20 left-10 w-20 h-20 border border-primary/20 rounded-full animate-spin-slow opacity-30"></div>
      <div className="absolute bottom-20 right-10 w-32 h-32 border border-primary/20 rounded-full animate-spin-slow opacity-30" style={{ animationDelay: '3s', animationDuration: '15s' }}></div>
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center max-w-3xl mx-auto">
          {/* Badge */}
          <span className="inline-flex items-center mb-4 px-3 py-1 rounded-full text-sm font-medium bg-primary/10 text-primary">
            <FaShieldAlt size={16} className="mr-1 animate-bounce-subtle" />
            Security Compliance Made Simple
          </span>
          
          {/* Main heading */}
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-6">
            Automate Your <span className="moving-gradient">Security Compliance</span> Today
          </h1>
          
          {/* Description */}
          <p className="text-lg md:text-xl text-muted-foreground mb-8">
            Streamline your security compliance with our advanced automation tools. Save time, reduce errors, and stay secure with Complytics.
          </p>
          
          {/* Buttons */}
          <div className="flex flex-col sm:flex-row justify-center gap-4 mb-10">
            <Button size="lg" className="gradient-button group">
              Request Access
              <FaArrowRight size={16} className="ml-2 transition-transform duration-300 group-hover:translate-x-1" />
            </Button>
            <Button variant="outline" size="lg" className="animated-border">
              Watch Demo
            </Button>
          </div>
          
          {/* Features list */}
          <div className="flex flex-col sm:flex-row justify-center gap-x-6 gap-y-3 text-sm text-muted-foreground">
            <div className="flex items-center">
              <FaCheckCircle size={16} className="text-primary mr-2 animate-pulse-slow" />
              <span>No lengthy onboarding required</span>
            </div>
            <div className="flex items-center">
              <FaCheckCircle size={16} className="text-primary mr-2 animate-pulse-slow" style={{ animationDelay: '1s' }} />
              <span>Watch how Complytics works</span>
            </div>
            <div className="flex items-center">
              <FaLock size={16} className="text-primary mr-2 animate-pulse-slow" style={{ animationDelay: '2s' }} />
              <span>Submit your request to get started</span>
            </div>
          </div>
        </div>
        
        {/* Dashboard preview */}
        <div className="mt-16 max-w-4xl mx-auto relative">
          <div className="animated-border rounded-xl overflow-hidden shadow-2xl hover-card">
            <div className="relative bg-gray-800 h-8 flex items-center px-4">
              <div className="flex space-x-2 absolute left-4">
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
              </div>
              <div className="w-full text-center text-gray-400 text-xs">complytics.app</div>
            </div>
            <div className="bg-gray-900 h-72 md:h-96 flex items-center justify-center overflow-hidden">
              <div className="text-center text-white">
                <div className="w-20 h-20 bg-primary/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <FaShieldAlt className="h-10 w-10 text-primary animate-float" />
                </div>
                <p className="text-lg font-medium">Complytics Dashboard Preview</p>
                <p className="text-sm text-gray-400 mt-2">Powerful compliance automation at your fingertips</p>
              </div>
              
              <div className="absolute top-1/4 left-1/4 w-1/2 h-1/2 bg-gradient-to-r from-primary/10 to-transparent rounded-full blur-3xl animate-spin-slow opacity-30"></div>
            </div>
          </div>
          
          <div className="absolute -top-6 -left-6 w-24 h-24 bg-primary/10 rounded-full blur-xl animate-pulse-slow"></div>
          <div className="absolute -bottom-6 -right-6 w-32 h-32 bg-primary/10 rounded-full blur-xl animate-pulse-slow" style={{ animationDelay: '2s' }}></div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;