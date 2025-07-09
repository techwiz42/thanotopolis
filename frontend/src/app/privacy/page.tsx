'use client';

export default function PrivacyPolicy() {
  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
        <h1 className="text-3xl font-bold mb-8">Privacy Policy</h1>
        
        <div className="prose prose-gray max-w-none">
          <p className="text-sm text-gray-500 mb-6">
            Last updated: {new Date().toLocaleDateString()}
          </p>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Introduction</h2>
            <p className="mb-4">
              At Thanotopolis, we take your privacy seriously. This Privacy Policy explains how we collect, 
              use, disclose, and safeguard your information when you use our AI conversation platform.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Information We Collect</h2>
            
            <h3 className="text-xl font-medium mb-3">Personal Information</h3>
            <ul className="list-disc pl-6 mb-4">
              <li>Account information (username, email, password)</li>
              <li>Profile information you choose to provide</li>
              <li>Communication preferences</li>
            </ul>

            <h3 className="text-xl font-medium mb-3">Usage Information</h3>
            <ul className="list-disc pl-6 mb-4">
              <li>Conversation history and messages</li>
              <li>Voice recordings (when using speech-to-text features)</li>
              <li>Usage patterns and interaction data</li>
              <li>Device information and browser data</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">How We Use Your Information</h2>
            <ul className="list-disc pl-6 mb-4">
              <li>To provide and improve our AI conversation services</li>
              <li>To personalize your experience</li>
              <li>To process voice input and generate responses</li>
              <li>To maintain conversation history</li>
              <li>To communicate with you about service updates</li>
              <li>To ensure platform security and prevent abuse</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Voice Data Processing</h2>
            <p className="mb-4">
              When you use our speech-to-text features:
            </p>
            <ul className="list-disc pl-6 mb-4">
              <li>Voice recordings are processed in real-time for transcription</li>
              <li>Audio data is transmitted securely to our speech processing service</li>
              <li>Voice recordings are not permanently stored on our servers</li>
              <li>Transcribed text may be retained as part of your conversation history</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Data Sharing and Disclosure</h2>
            <p className="mb-4">We do not sell your personal information. We may share information in these circumstances:</p>
            <ul className="list-disc pl-6 mb-4">
              <li>With third-party service providers who assist in operating our platform</li>
              <li>When required by law or to protect our rights</li>
              <li>With your consent for specific purposes</li>
              <li>In connection with a business transfer or merger</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Data Security</h2>
            <p className="mb-4">
              We implement appropriate technical and organizational measures to protect your information:
            </p>
            <ul className="list-disc pl-6 mb-4">
              <li>Encryption of data in transit and at rest</li>
              <li>Secure authentication and access controls</li>
              <li>Regular security assessments and updates</li>
              <li>Limited access to personal information on a need-to-know basis</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Your Rights and Choices</h2>
            <p className="mb-4">You have the right to:</p>
            <ul className="list-disc pl-6 mb-4">
              <li>Access and review your personal information</li>
              <li>Correct inaccurate or incomplete information</li>
              <li>Delete your account and associated data</li>
              <li>Export your conversation history</li>
              <li>Opt out of certain communications</li>
              <li>Disable voice features at any time</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Data Retention</h2>
            <p className="mb-4">
              We retain your information for as long as necessary to provide our services and comply with legal obligations:
            </p>
            <ul className="list-disc pl-6 mb-4">
              <li>Account information: Until you delete your account</li>
              <li>Conversation history: Until you delete conversations or your account</li>
              <li>Usage logs: Typically 90 days for security and service improvement</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Cookies and Tracking</h2>
            <p className="mb-4">
              We use cookies and similar technologies to enhance your experience, maintain sessions, 
              and analyze usage patterns. You can control cookie settings through your browser.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Email Tracking</h2>
            <p className="mb-4">
              We may include unique tracking technologies, such as pixels or web beacons, in our email 
              communications. These technologies help us determine whether our emails have been opened 
              and if any links were clicked. We use this information to measure the effectiveness of 
              our communications, improve our services, and tailor future messages to better suit your 
              interests. You can disable email tracking by adjusting your email client settings to 
              block images or by choosing to receive plain-text emails where available.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Children's Privacy</h2>
            <p className="mb-4">
              Our service is not intended for children under 13. We do not knowingly collect 
              personal information from children under 13. If we become aware of such collection, 
              we will delete the information promptly.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">International Data Transfers</h2>
            <p className="mb-4">
              Your information may be transferred to and processed in countries other than your own. 
              We ensure appropriate safeguards are in place to protect your information during such transfers.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Changes to This Policy</h2>
            <p className="mb-4">
              We may update this Privacy Policy from time to time. We will notify you of any material 
              changes by posting the new policy on this page and updating the "Last updated" date.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Contact Us</h2>
            <p className="mb-4">
              If you have any questions about this Privacy Policy or our data practices, please contact us at:
            </p>
            <p className="mb-4">
              <a href="mailto:pete@cyberiad.ai" className="text-blue-600 hover:text-blue-800 underline">
                pete@cyberiad.ai
              </a>
            </p>
          </section>
        </div>
    </div>
  );
}