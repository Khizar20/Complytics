import React, { useState } from 'react';
import { FaShieldAlt, FaTwitter, FaLinkedin, FaGithub, FaEnvelope } from 'react-icons/fa';
import Modal from '../ui/Modal';

const Footer = () => {
  const currentYear = new Date().getFullYear();
  const [isPrivacyOpen, setIsPrivacyOpen] = useState(false);
  const [isTermsOpen, setIsTermsOpen] = useState(false);
  
  return (
    <footer className="bg-secondary/60 py-16 relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10">
          <div className="lg:col-span-2">
            <div className="flex items-center space-x-2 mb-4">
              <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
                <FaShieldAlt className="h-4 w-4 text-white" />
              </div>
              <span className="font-bold text-lg text-foreground">complytics</span>
            </div>
            
            <p className="text-muted-foreground mb-6 max-w-md">
              Streamline your security compliance with our advanced automation tools. 
              Complytics helps you stay secure without the heavy manual workload.
            </p>
            
            <div className="flex space-x-4">
              <a href="#" className="p-2 text-muted-foreground hover:text-primary transition-colors" aria-label="Twitter">
                <FaTwitter size={20} />
              </a>
              <a href="#" className="p-2 text-muted-foreground hover:text-primary transition-colors" aria-label="LinkedIn">
                <FaLinkedin size={20} />
              </a>
              <a href="#" className="p-2 text-muted-foreground hover:text-primary transition-colors" aria-label="GitHub">
                <FaGithub size={20} />
              </a>
              <a href="#" className="p-2 text-muted-foreground hover:text-primary transition-colors" aria-label="Email">
                <FaEnvelope size={20} />
              </a>
            </div>
          </div>
          
          <div>
            <h3 className="font-semibold mb-4">Product</h3>
            <ul className="space-y-3">
              <li>
                <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
                  Features
                </a>
              </li>
            </ul>
          </div>
          
          <div>
            <h3 className="font-semibold mb-4">Company</h3>
            <ul className="space-y-3">
              <li>
                <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
                  About
                </a>
              </li>
              <li>
                <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
                  Contact
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold mb-4">Legal</h3>
            <ul className="space-y-3">
              <li>
                <button 
                  onClick={() => setIsPrivacyOpen(true)}
                  className="text-muted-foreground hover:text-primary transition-colors"
                >
                  Privacy
                </button>
              </li>
              <li>
                <button 
                  onClick={() => setIsTermsOpen(true)}
                  className="text-muted-foreground hover:text-primary transition-colors"
                >
                  Terms
                </button>
              </li>
            </ul>
          </div>
        </div>
        
        <div className="mt-12 pt-8 border-t border-border">
          <p className="text-center text-muted-foreground">
            © {currentYear} Complytics. All rights reserved.
          </p>
        </div>
      </div>

      {/* Privacy Policy Modal */}
      <Modal
        isOpen={isPrivacyOpen}
        onClose={() => setIsPrivacyOpen(false)}
        title="Privacy Policy"
      >
        <div className="space-y-4 text-gray-600 dark:text-gray-300">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">1. Information We Collect</h3>
          <p>
            We collect information that you provide directly to us, including but not limited to:
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>Name and contact information</li>
            <li>Organization details</li>
            <li>Account credentials</li>
            <li>Usage data and analytics</li>
          </ul>

          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mt-6">2. How We Use Your Information</h3>
          <p>
            We use the collected information to:
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>Provide and maintain our services</li>
            <li>Improve and personalize user experience</li>
            <li>Communicate with you about our services</li>
            <li>Ensure security and prevent fraud</li>
          </ul>

          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mt-6">3. Data Security</h3>
          <p>
            We implement appropriate security measures to protect your personal information from unauthorized access, alteration, disclosure, or destruction.
          </p>

          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mt-6">4. Your Rights</h3>
          <p>
            You have the right to:
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>Access your personal information</li>
            <li>Correct inaccurate data</li>
            <li>Request deletion of your data</li>
            <li>Opt-out of marketing communications</li>
          </ul>
        </div>
      </Modal>

      {/* Terms of Service Modal */}
      <Modal
        isOpen={isTermsOpen}
        onClose={() => setIsTermsOpen(false)}
        title="Terms of Service"
      >
        <div className="space-y-4 text-gray-600 dark:text-gray-300">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">1. Acceptance of Terms</h3>
          <p>
            By accessing and using Complytics, you agree to be bound by these Terms of Service and all applicable laws and regulations.
          </p>

          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mt-6">2. Use of Service</h3>
          <p>
            You agree to use the service only for lawful purposes and in accordance with these Terms. You shall not:
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>Violate any applicable laws or regulations</li>
            <li>Infringe upon the rights of others</li>
            <li>Interfere with the proper functioning of the service</li>
            <li>Attempt to gain unauthorized access</li>
          </ul>

          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mt-6">3. Account Responsibilities</h3>
          <p>
            You are responsible for:
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>Maintaining the confidentiality of your account</li>
            <li>All activities that occur under your account</li>
            <li>Providing accurate and complete information</li>
            <li>Notifying us of any security breaches</li>
          </ul>

          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mt-6">4. Service Modifications</h3>
          <p>
            We reserve the right to modify or discontinue the service at any time without notice. We shall not be liable to you or any third party for any modification, suspension, or discontinuance of the service.
          </p>
        </div>
      </Modal>
    </footer>
  );
};

export default Footer;