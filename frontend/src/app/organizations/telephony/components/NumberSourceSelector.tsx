'use client';

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Phone, ShoppingCart, Clock, CheckCircle } from 'lucide-react';

export type NumberSourceType = 'existing' | 'purchase';

interface NumberSourceOption {
  type: NumberSourceType;
  title: string;
  description: string;
  features: string[];
  badges: { text: string; variant: 'default' | 'secondary' | 'outline' }[];
  icon: React.ReactNode;
}

interface NumberSourceSelectorProps {
  value: NumberSourceType;
  onChange: (value: NumberSourceType) => void;
  disabled?: boolean;
}

const NUMBER_SOURCE_OPTIONS: NumberSourceOption[] = [
  {
    type: 'existing',
    title: 'Use Existing Business Number',
    description: 'Forward calls from your current business phone number to our AI system',
    features: [
      'Keep your existing phone number',
      'Customers call your familiar number',
      'Requires call forwarding setup',
      'SMS verification required'
    ],
    badges: [
      { text: 'Most Common', variant: 'default' },
      { text: 'Setup Required', variant: 'outline' }
    ],
    icon: <Phone className="h-6 w-6" />
  },
  {
    type: 'purchase',
    title: 'Purchase New Twilio Number',
    description: 'Get a new phone number from Twilio for dedicated AI call handling',
    features: [
      'Instant setup, no verification needed',
      'Choose from available area codes',
      'Professional local or toll-free numbers',
      'Monthly fee applies (~$1-15/month)'
    ],
    badges: [
      { text: 'Instant Setup', variant: 'default' },
      { text: 'Additional Cost', variant: 'secondary' }
    ],
    icon: <ShoppingCart className="h-6 w-6" />
  }
];

export default function NumberSourceSelector({ value, onChange, disabled = false }: NumberSourceSelectorProps) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Choose Phone Number Option</h3>
        <p className="text-sm text-muted-foreground">
          Select how you want to set up phone calls for your organization
        </p>
      </div>

      <RadioGroup
        value={value}
        onValueChange={onChange}
        disabled={disabled}
        className="space-y-4"
      >
        {NUMBER_SOURCE_OPTIONS.map((option) => (
          <div key={option.type} className="relative">
            <RadioGroupItem
              value={option.type}
              id={option.type}
              className="peer sr-only"
            />
            <Label
              htmlFor={option.type}
              className="block cursor-pointer"
            >
              <Card className="transition-all hover:shadow-md peer-checked:ring-2 peer-checked:ring-primary peer-checked:border-primary peer-disabled:cursor-not-allowed peer-disabled:opacity-50">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex-shrink-0 text-primary">
                        {option.icon}
                      </div>
                      <div>
                        <CardTitle className="text-base">{option.title}</CardTitle>
                        <CardDescription className="text-sm">
                          {option.description}
                        </CardDescription>
                      </div>
                    </div>
                    <div className="flex flex-col gap-1">
                      {option.badges.map((badge, index) => (
                        <Badge key={index} variant={badge.variant} className="text-xs">
                          {badge.text}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <ul className="space-y-1">
                    {option.features.map((feature, index) => (
                      <li key={index} className="flex items-center gap-2 text-sm text-muted-foreground">
                        <CheckCircle className="h-3 w-3 text-green-500 flex-shrink-0" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </Label>
          </div>
        ))}
      </RadioGroup>

      {value === 'existing' && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <Clock className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm">
              <p className="font-medium text-blue-900">Setup Process</p>
              <p className="text-blue-700 mt-1">
                You'll need to verify your number via SMS and set up call forwarding with your carrier. 
                The process typically takes 5-15 minutes.
              </p>
            </div>
          </div>
        </div>
      )}

      {value === 'purchase' && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm">
              <p className="font-medium text-green-900">Instant Setup</p>
              <p className="text-green-700 mt-1">
                Choose from available numbers in your preferred area code. Setup is immediate with no verification required.
                Monthly fees range from $1 (local) to $15 (toll-free).
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}