'use client';

export default function TermsOfService() {
  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
        <h1 className="text-3xl font-bold mb-8">Terms of Service</h1>
        
        <div className="prose prose-gray max-w-none">
          <p className="text-sm text-gray-500 mb-6">
            Last updated: {new Date().toLocaleDateString()}
          </p>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Agreement to Terms</h2>
            <p className="mb-4">
              By accessing and using Thanotopolis, you accept and agree to be bound by the terms and 
              provision of this agreement. If you do not agree to abide by the above, please do not 
              use this service.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Description of Service</h2>
            <p className="mb-4">
              Thanotopolis is an AI-powered conversation platform that enables users to engage in 
              interactive dialogues with artificial intelligence systems. Our service includes 
              text-based conversations, voice input/output capabilities, and conversation management features.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">User Accounts and Registration</h2>
            <ul className="list-disc pl-6 mb-4">
              <li>You must provide accurate and complete information when creating an account</li>
              <li>You are responsible for maintaining the security of your account credentials</li>
              <li>You must notify us immediately of any unauthorized use of your account</li>
              <li>You may not share your account with others or create multiple accounts</li>
              <li>We reserve the right to suspend or terminate accounts that violate these terms</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Acceptable Use Policy</h2>
            <p className="mb-4">You agree NOT to use our service to:</p>
            <ul className="list-disc pl-6 mb-4">
              <li>Generate, promote, or distribute illegal, harmful, or offensive content</li>
              <li>Attempt to manipulate, exploit, or abuse our AI systems</li>
              <li>Violate any applicable laws or regulations</li>
              <li>Infringe upon the rights of others, including intellectual property rights</li>
              <li>Spam, harass, or abuse other users or our support team</li>
              <li>Attempt to gain unauthorized access to our systems or data</li>
              <li>Use automated tools to access our service without permission</li>
              <li>Generate content that could harm minors</li>
              <li>Create or distribute malware, viruses, or other harmful code</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Content and Intellectual Property</h2>
            
            <h3 className="text-xl font-medium mb-3">Your Content</h3>
            <ul className="list-disc pl-6 mb-4">
              <li>You retain ownership of content you create and input into our service</li>
              <li>You grant us a license to use your content to provide and improve our services</li>
              <li>You are responsible for ensuring your content does not violate any laws or third-party rights</li>
            </ul>

            <h3 className="text-xl font-medium mb-3">AI-Generated Content</h3>
            <ul className="list-disc pl-6 mb-4">
              <li>AI-generated responses are provided for informational and entertainment purposes</li>
              <li>We do not claim ownership of AI-generated content</li>
              <li>You should not rely solely on AI-generated content for important decisions</li>
              <li>AI responses may contain inaccuracies or reflect biases in training data</li>
            </ul>

            <h3 className="text-xl font-medium mb-3">Our Intellectual Property</h3>
            <ul className="list-disc pl-6 mb-4">
              <li>The Thanotopolis platform, software, and branding are our intellectual property</li>
              <li>You may not copy, modify, or distribute our proprietary technology</li>
              <li>All rights not expressly granted to you are reserved by us</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Voice Services</h2>
            <p className="mb-4">When using our voice features:</p>
            <ul className="list-disc pl-6 mb-4">
              <li>You consent to the processing of your voice data for transcription purposes</li>
              <li>Voice recognition accuracy may vary based on accent, background noise, and other factors</li>
              <li>You may disable voice features at any time in your account settings</li>
              <li>We are not responsible for errors in voice recognition or transcription</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Privacy and Data Protection</h2>
            <p className="mb-4">
              Your privacy is important to us. Please review our Privacy Policy to understand how we 
              collect, use, and protect your information. By using our service, you consent to the 
              collection and use of information as described in our Privacy Policy.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Service Availability and Modifications</h2>
            <ul className="list-disc pl-6 mb-4">
              <li>We strive to maintain high service availability but cannot guarantee 100% uptime</li>
              <li>We may temporarily suspend service for maintenance or updates</li>
              <li>We reserve the right to modify, suspend, or discontinue features at any time</li>
              <li>We will provide reasonable notice of significant changes when possible</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Disclaimers and Limitations</h2>
            
            <h3 className="text-xl font-medium mb-3">AI Limitations</h3>
            <ul className="list-disc pl-6 mb-4">
              <li>AI responses are generated based on patterns in training data and may not be accurate</li>
              <li>Our AI systems may produce biased, inappropriate, or incorrect responses</li>
              <li>AI-generated content should not be considered professional advice</li>
              <li>We do not guarantee the quality, accuracy, or reliability of AI responses</li>
            </ul>

            <h3 className="text-xl font-medium mb-3">Service Disclaimers</h3>
            <ul className="list-disc pl-6 mb-4">
              <li>Our service is provided "as is" without warranties of any kind</li>
              <li>We disclaim all warranties, express or implied, including merchantability and fitness for purpose</li>
              <li>We are not responsible for any damages resulting from your use of our service</li>
              <li>Your use of our service is at your own risk</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Liability Limitations</h2>
            <p className="mb-4">
              To the maximum extent permitted by law, our liability for any damages arising from or 
              related to your use of our service is limited to the amount you paid us in the 12 months 
              preceding the claim. We are not liable for indirect, incidental, special, or consequential damages.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Indemnification</h2>
            <p className="mb-4">
              You agree to indemnify and hold us harmless from any claims, damages, or expenses arising 
              from your use of our service, your violation of these terms, or your violation of any 
              rights of another party.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Termination</h2>
            <ul className="list-disc pl-6 mb-4">
              <li>You may terminate your account at any time by contacting us</li>
              <li>We may suspend or terminate your account for violations of these terms</li>
              <li>Upon termination, your right to use our service ceases immediately</li>
              <li>We may retain certain information as required by law or for legitimate business purposes</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Governing Law and Disputes</h2>
            <p className="mb-4">
              These terms are governed by the laws of the State of California. Any disputes arising from these 
              terms or your use of our service will be resolved through binding arbitration or in the 
              courts of the State of California.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Changes to Terms</h2>
            <p className="mb-4">
              We may update these Terms of Service from time to time. We will notify you of any material 
              changes by posting the new terms on this page and updating the "Last updated" date. 
              Your continued use of our service after such changes constitutes acceptance of the new terms.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Severability</h2>
            <p className="mb-4">
              If any provision of these terms is found to be unenforceable, the remaining provisions 
              will remain in full force and effect.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Contact Information</h2>
            <p className="mb-4">
              If you have any questions about these Terms of Service, please contact us at:
            </p>
            <p className="mb-4">
              <a href="mailto:pete@cyberiad.ai" className="text-blue-600 hover:text-blue-800 underline">
                pete@cyberiad.ai
              </a>
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Effective Date</h2>
            <p className="mb-4">
              These Terms of Service are effective as of the date last updated above and remain in 
              effect until modified or terminated.
            </p>
          </section>
        </div>
    </div>
  );
}