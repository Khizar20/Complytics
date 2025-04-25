import React, { useEffect, useState } from 'react';
import { Button } from "../ui/button.jsx";
import { FaArrowRight, FaEnvelope, FaShieldAlt, FaClock } from 'react-icons/fa';

const CTASection = () => {
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    company: '',
    domain: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState(null);
  const [error, setError] = useState(null);

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

  const handleInputChange = (e) => {
    const { id, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [id]: value
    }));
    // Clear error when user starts typing
    if (error) setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setSubmitStatus(null);

    try {
      // Transform the form data to match the UserCreate schema
      const userData = {
        email: formData.email,
        first_name: formData.firstName,
        last_name: formData.lastName,
        organization_name: formData.company,
        organization_domain: formData.domain,
        password: Math.random().toString(36).slice(-8) // Generate a random password
      };

      const response = await fetch('http://localhost:8000/registration/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(userData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to submit registration');
      }

      setSubmitStatus('success');
      // Clear form
      setFormData({
        firstName: '',
        lastName: '',
        email: '',
        company: '',
        domain: ''
      });
    } catch (err) {
      setError(err.message || 'Failed to submit registration. Please try again.');
      console.error('Registration error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section id="contact" className="section py-24 relative overflow-hidden">
      <div className="gradient-blur bottom-0 left-1/4 opacity-40"></div>
      
      <div className="grid md:grid-cols-2 gap-12 items-center">
        <div>
          <h2 className="section-title">Ready to Simplify Your Compliance Journey?</h2>
          <p className="section-subtitle mb-8">
            Join hundreds of organizations that have transformed their security compliance with Complytics.
          </p>
          
          <div className="space-y-6 mb-8">
            <div className="flex items-start">
              <div className="mr-4 mt-1 p-2 bg-primary/10 rounded-full">
                <FaShieldAlt size={20} className="text-primary" />
              </div>
              <div>
                <h3 className="font-medium">Enhance Your Security Posture</h3>
                <p className="text-muted-foreground">Maintain continuous compliance with automated security checks and remediation.</p>
              </div>
            </div>
            
            <div className="flex items-start">
              <div className="mr-4 mt-1 p-2 bg-primary/10 rounded-full">
                <FaClock size={20} className="text-primary" />
              </div>
              <div>
                <h3 className="font-medium">Save Valuable Time</h3>
                <p className="text-muted-foreground">Reduce manual compliance efforts by up to 80% with our automation platform.</p>
              </div>
            </div>
            
            <div className="flex items-start">
              <div className="mr-4 mt-1 p-2 bg-primary/10 rounded-full">
                <FaEnvelope size={20} className="text-primary" />
              </div>
              <div>
                <h3 className="font-medium">Expert Support</h3>
                <p className="text-muted-foreground">Our compliance experts are ready to guide you through your security journey.</p>
              </div>
            </div>
          </div>
          
          <Button className="group" size="lg">
            <span>Schedule a Demo</span>
            <FaArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
          </Button>
        </div>
        
        <div>
          <div className="glass-card rounded-xl p-8 md:p-10">
            <h3 className="text-xl font-semibold mb-6">Get in Touch</h3>
            
            <form className="space-y-5" onSubmit={handleSubmit}>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label htmlFor="firstName" className="text-sm font-medium">
                    First Name
                  </label>
                  <input
                    id="firstName"
                    type="text"
                    required
                    value={formData.firstName}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-primary/50"
                    placeholder="John"
                  />
                </div>
                
                <div className="space-y-2">
                  <label htmlFor="lastName" className="text-sm font-medium">
                    Last Name
                  </label>
                  <input
                    id="lastName"
                    type="text"
                    required
                    value={formData.lastName}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-primary/50"
                    placeholder="Smith"
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium">
                  Work Email
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={formData.email}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="john@company.com"
                />
              </div>
              
              <div className="space-y-2">
                <label htmlFor="company" className="text-sm font-medium">
                  Company
                </label>
                <input
                  id="company"
                  type="text"
                  required
                  value={formData.company}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="Acme Inc."
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="domain" className="text-sm font-medium">
                  Company Domain
                </label>
                <input
                  id="domain"
                  type="text"
                  required
                  value={formData.domain}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="acme.com"
                />
              </div>
              
              <Button 
                className="w-full" 
                size="lg" 
                type="submit"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Submitting...' : 'Submit Registration'}
              </Button>

              {error && (
                <p className="text-sm text-red-500 text-center mt-2">
                  {error}
                </p>
              )}

              {submitStatus === 'success' && (
                <p className="text-sm text-green-500 text-center mt-2">
                  Thank you for your registration! We'll review your application and get back to you soon.
                </p>
              )}
            </form>
            
            <p className="text-xs text-center text-muted-foreground mt-6">
              By submitting this form, you agree to our {" "}
              <a href="#" className="text-primary hover:underline">
                Privacy Policy
              </a>
              .
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default CTASection;