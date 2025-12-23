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
    <section ref={heroRef} className="relative overflow-hidden pt-28 pb-16 md:pt-36 md:pb-24 bg-gradient-to-b from-blue-50/30 via-blue-50/50 to-blue-50/30">
      {/* Animated background elements */}
      <div className="absolute top-0 left-1/3 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
      <div className="absolute bottom-0 right-1/3 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '2s' }}></div>
      
      {/* Decorative circles */}
      <div className="absolute top-20 left-10 w-20 h-20 border-2 border-blue-500/20 rounded-full animate-spin-slow opacity-30"></div>
      <div className="absolute bottom-20 right-10 w-32 h-32 border-2 border-blue-500/20 rounded-full animate-spin-slow opacity-30" style={{ animationDelay: '3s', animationDuration: '15s' }}></div>
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center max-w-4xl mx-auto">
          {/* Badge */}
          <span className="inline-flex items-center mb-6 px-4 py-2 rounded-full text-sm font-medium bg-blue-100 text-blue-700 border border-blue-200">
            <FaShieldAlt size={16} className="mr-2 animate-bounce-subtle" />
            Security Compliance Made Simple
          </span>
          
          {/* Main Complytics heading */}
          <h1 className="text-6xl md:text-7xl lg:text-8xl xl:text-9xl font-bold tracking-tight mb-6 leading-tight">
            <span className="inline-block">
              <span className="inline-block bg-gradient-to-br from-blue-600 via-blue-500 to-blue-700 text-white px-4 py-2 md:px-6 md:py-3 rounded-2xl md:rounded-3xl shadow-2xl transform rotate-[-2deg] mr-2 md:mr-3">
                C
              </span>
              <span className="text-black">omplytics</span>
            </span>
          </h1>
          
          {/* Subheading */}
          <h2 className="text-2xl md:text-3xl lg:text-4xl font-semibold tracking-tight mb-6 text-gray-800">
            AI-Powered Compliance Management Platform
          </h2>
          
          {/* Description */}
          <p className="text-lg md:text-xl text-gray-600 mb-10 max-w-2xl mx-auto">
            Streamline your security compliance with our advanced automation tools. Save time, reduce errors, and stay secure with Complytics.
          </p>
          
          {/* Buttons */}
          <div className="flex flex-col sm:flex-row justify-center gap-4 mb-12">
            <Button 
              size="lg" 
              className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-6 text-lg font-semibold shadow-lg hover:shadow-xl transition-all duration-300 group"
              onClick={() => {
                const contactSection = document.getElementById('contact');
                if (contactSection) {
                  contactSection.scrollIntoView({ behavior: 'smooth' });
                }
              }}
            >
              Request Access
              <FaArrowRight size={18} className="ml-2 transition-transform duration-300 group-hover:translate-x-1" />
            </Button>
            <Button variant="outline" size="lg" className="border-2 border-black text-black hover:bg-black hover:text-white px-8 py-6 text-lg font-semibold transition-all duration-300">
              Watch Demo
            </Button>
          </div>
          
          {/* Features list */}
          <div className="flex flex-col sm:flex-row justify-center gap-x-8 gap-y-4 text-base text-gray-700 font-medium">
            <div className="flex items-center justify-center">
              <FaCheckCircle size={18} className="text-blue-600 mr-2 animate-pulse-slow" />
              <span>No lengthy onboarding required</span>
            </div>
            <div className="flex items-center justify-center">
              <FaCheckCircle size={18} className="text-blue-600 mr-2 animate-pulse-slow" style={{ animationDelay: '1s' }} />
              <span>Watch how Complytics works</span>
            </div>
            <div className="flex items-center justify-center">
              <FaLock size={18} className="text-blue-600 mr-2 animate-pulse-slow" style={{ animationDelay: '2s' }} />
              <span>Submit your request to get started</span>
            </div>
          </div>
        </div>
        
        {/* Dashboard preview */}
        <div className="mt-20 max-w-5xl mx-auto relative">
          <div className="border-2 border-black rounded-xl overflow-hidden shadow-2xl hover:shadow-3xl transition-all duration-300 hover:-translate-y-2">
            <div className="relative bg-black h-10 flex items-center px-4">
              <div className="flex space-x-2 absolute left-4">
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
              </div>
              <div className="w-full text-center text-white text-sm font-medium">complytics.app</div>
            </div>
            <div className="bg-gradient-to-br from-white to-blue-50/70 h-80 md:h-[500px] flex items-center justify-center overflow-hidden border-t-2 border-black">
              <div className="text-center">
                <div className="w-24 h-24 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
                  <FaShieldAlt className="h-12 w-12 text-white animate-float" />
                </div>
                <p className="text-2xl font-bold text-black mb-2">Complytics Dashboard Preview</p>
                <p className="text-base text-gray-600">Powerful compliance automation at your fingertips</p>
              </div>
              
              <div className="absolute top-1/4 left-1/4 w-1/2 h-1/2 bg-blue-500/20 rounded-full blur-3xl animate-spin-slow opacity-40"></div>
            </div>
          </div>
          
          <div className="absolute -top-6 -left-6 w-24 h-24 bg-blue-500/20 rounded-full blur-xl animate-pulse-slow"></div>
          <div className="absolute -bottom-6 -right-6 w-32 h-32 bg-blue-600/20 rounded-full blur-xl animate-pulse-slow" style={{ animationDelay: '2s' }}></div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;