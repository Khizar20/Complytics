// Top of every component file
import React from 'react'
import Navbar from './components/layout/Navbar'
import HeroSection from './components/sections/HeroSection'
import FeaturesSection from './components/sections/FeaturesSection'
import TestimonialsSection from './components/sections/TestimonialsSection'
import CTASection from './components/sections/CTASection'
import Footer from './components/layout/Footer'
import CustomCursor from './components/ui/CustomCursor'

function App() {
  return (
    <div className="min-h-screen bg-background">
      <CustomCursor />
      <Navbar />
      <main className="relative">
        <HeroSection />
        <FeaturesSection />
        <TestimonialsSection />
        <CTASection />
      </main>
      <Footer />
    </div>
  )
}

export default App