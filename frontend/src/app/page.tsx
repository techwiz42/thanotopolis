'use client'

import React from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function Home() {
  return (
    <div className="bg-gray-50 min-h-screen">
      {/* Hero Section */}
      <div className="bg-gradient-to-b from-slate-700 to-slate-600 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="text-center space-y-8">
            <div className="flex justify-center">
              <img 
                src="/winged-solar-disk.png"
                alt="Winged Solar Disk"
                className="w-auto h-20 opacity-90"
              />
            </div>
            
            <div className="space-y-6">
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight">
                AI Chat and Voice for Cemeteries
                <span className="block text-yellow-400">— in Any Language</span>
              </h1>
              
              <p className="text-xl sm:text-2xl text-gray-200 max-w-4xl mx-auto leading-relaxed">
                Serve diverse families with culturally sensitive, multilingual AI assistants. 
                Reduce calls, save staff time, and build trust with grieving families.
              </p>
              
              <p className="text-lg text-gray-300 max-w-3xl mx-auto">
                Thanotopolis is designed specifically for cemeteries, mortuaries, and funeral homes 
                serving multicultural communities.
              </p>
            </div>
            
            <div className="flex justify-center items-center pt-4">
              <Link href="#benefits">
                <Button size="lg" className="bg-yellow-500 hover:bg-yellow-600 text-slate-900 font-semibold px-8 py-3 text-lg">
                  See It in Action
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Benefits Section */}
      <div id="benefits" className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center space-y-4 mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">
              Why Cemeteries Choose Thanotopolis
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Built specifically for the unique needs of cemetery and funeral home customer service
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <Card className="border-2 hover:border-slate-300 transition-colors">
              <CardHeader>
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                  </svg>
                </div>
                <CardTitle>Serve Families in Multiple Languages</CardTitle>
                <CardDescription>
                  Spanish, Armenian, Tagalog, Vietnamese, Mandarin, and more — while your staff works in English
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="border-2 hover:border-slate-300 transition-colors">
              <CardHeader>
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <CardTitle>Reduce Repetitive Phone Calls</CardTitle>
                <CardDescription>
                  Automatically answer questions about hours, burial plot availability, pricing, and cemetery rules
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="border-2 hover:border-slate-300 transition-colors">
              <CardHeader>
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                  </svg>
                </div>
                <CardTitle>Culturally Sensitive Service</CardTitle>
                <CardDescription>
                  Understand cultural burial traditions, religious requirements, and family customs across communities
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="border-2 hover:border-slate-300 transition-colors">
              <CardHeader>
                <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <CardTitle>Improve Family Satisfaction</CardTitle>
                <CardDescription>
                  Provide immediate, accurate responses 24/7 in the language families are most comfortable with
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="border-2 hover:border-slate-300 transition-colors">
              <CardHeader>
                <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <CardTitle>Keep Staff Productive</CardTitle>
                <CardDescription>
                  Let AI handle routine inquiries while your team focuses on complex family services and sales
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="border-2 hover:border-slate-300 transition-colors">
              <CardHeader>
                <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <CardTitle>24/7 Availability</CardTitle>
                <CardDescription>
                  Families can get help any time, day or night, through chat, voice calls, or website integration
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>
      </div>

      {/* Use Cases Section */}
      <div className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center space-y-4 mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">
              How Cemeteries Use Thanotopolis
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Real-world applications that save time and improve family experience
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 gap-12">
            <div className="space-y-6">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                  <span className="text-white font-semibold">1</span>
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Answer Routine Family Questions</h3>
                  <p className="text-gray-600">Cemetery hours, visiting rules, burial plot pricing, interment scheduling, and monument regulations</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                  <span className="text-white font-semibold">2</span>
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Handle Multilingual Inquiries</h3>
                  <p className="text-gray-600">Serve Spanish-speaking, Armenian, Vietnamese, and other community families in their preferred language</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                  <span className="text-white font-semibold">3</span>
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Provide Culturally Appropriate Responses</h3>
                  <p className="text-gray-600">Understand religious burial requirements, cultural traditions, and family customs across different communities</p>
                </div>
              </div>
            </div>
            
            <div className="space-y-6">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                  <span className="text-white font-semibold">4</span>
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Pre-Need and At-Need Services</h3>
                  <p className="text-gray-600">Guide families through mausoleum options, columbarium niches, and burial plot selection processes</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                  <span className="text-white font-semibold">5</span>
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Automate Customer Service Tasks</h3>
                  <p className="text-gray-600">Handle appointment scheduling, payment inquiries, and basic administrative questions automatically</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                  <span className="text-white font-semibold">6</span>
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Support Grieving Families</h3>
                  <p className="text-gray-600">Provide compassionate, patient assistance during difficult times with appropriate cultural sensitivity</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="py-20 bg-slate-700 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="space-y-6">
            <h2 className="text-3xl sm:text-4xl font-bold">
              Ready to Better Serve Your Community?
            </h2>
            <p className="text-xl text-gray-300 max-w-3xl mx-auto">
              Join forward-thinking cemeteries and funeral homes using AI to provide better, 
              more accessible family services.
            </p>
            <div className="flex justify-center items-center pt-4">
              <Link href="mailto:pete@cyberiad.ai?subject=Thanotopolis Demo Request">
                <Button size="lg" variant="outline" className="border-white text-white hover:bg-white hover:text-slate-700 px-8 py-3 text-lg">
                  Schedule a Demo Call
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="py-12 bg-gray-900 text-gray-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center space-y-4">
            <div className="flex justify-center">
              <img 
                src="/winged-solar-disk.png"
                alt="Winged Solar Disk"
                className="w-auto h-12 opacity-50"
              />
            </div>
            <p className="text-sm">
              © 2025 Thanotopolis. Serving cemetery and funeral home families with dignity and technology.
            </p>
            <div className="flex justify-center space-x-6 text-sm">
              <Link href="/privacy" className="hover:text-white">Privacy Policy</Link>
              <Link href="/terms" className="hover:text-white">Terms of Service</Link>
              <Link href="mailto:pete@cyberiad.ai" className="hover:text-white">Contact</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}