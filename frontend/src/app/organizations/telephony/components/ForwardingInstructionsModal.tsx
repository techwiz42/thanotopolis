import React from 'react';
import { Phone } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface ForwardingInstructionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  instructions: string;
  organizationNumber: string;
  platformNumber: string;
}

export const ForwardingInstructionsModal: React.FC<ForwardingInstructionsModalProps> = ({
  isOpen,
  onClose,
  instructions,
  organizationNumber,
  platformNumber
}) => {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center">
            <Phone className="w-5 h-5 mr-2" />
            Call Forwarding Setup Instructions
          </DialogTitle>
          <DialogDescription>
            Set up call forwarding to activate AI phone support for your business
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Summary */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-900">
              <strong>Your Organization Number:</strong> {organizationNumber}
              <br />
              <strong>Platform Number:</strong> {platformNumber}
            </p>
          </div>

          {/* Detailed Instructions */}
          <div className="prose prose-sm max-w-none">
            <pre className="whitespace-pre-wrap text-sm bg-gray-50 p-4 rounded-lg border">
              {instructions}
            </pre>
          </div>

          {/* Actions */}
          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};