// frontend/src/app/organizations/telephony/components/BusinessHoursEditor.tsx
'use client';

import React from 'react';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { BusinessHours } from '@/services/telephony';

interface BusinessHoursEditorProps {
  businessHours: BusinessHours;
  onChange: (hours: BusinessHours) => void;
}

const DAYS = [
  { key: 'monday', label: 'Monday' },
  { key: 'tuesday', label: 'Tuesday' },
  { key: 'wednesday', label: 'Wednesday' },
  { key: 'thursday', label: 'Thursday' },
  { key: 'friday', label: 'Friday' },
  { key: 'saturday', label: 'Saturday' },
  { key: 'sunday', label: 'Sunday' }
];

const TIME_OPTIONS = [
  '00:00', '00:30', '01:00', '01:30', '02:00', '02:30', '03:00', '03:30',
  '04:00', '04:30', '05:00', '05:30', '06:00', '06:30', '07:00', '07:30',
  '08:00', '08:30', '09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
  '12:00', '12:30', '13:00', '13:30', '14:00', '14:30', '15:00', '15:30',
  '16:00', '16:30', '17:00', '17:30', '18:00', '18:30', '19:00', '19:30',
  '20:00', '20:30', '21:00', '21:30', '22:00', '22:30', '23:00', '23:30'
];

export const BusinessHoursEditor: React.FC<BusinessHoursEditorProps> = ({
  businessHours,
  onChange
}) => {
  const updateDayHours = (day: string, field: 'start' | 'end', value: string) => {
    const newHours = {
      ...businessHours,
      [day]: {
        ...businessHours[day],
        [field]: value
      }
    };
    onChange(newHours);
  };

  const toggleDayClosed = (day: string, isClosed: boolean) => {
    const newHours = {
      ...businessHours,
      [day]: isClosed 
        ? { start: 'closed', end: 'closed' }
        : { start: '09:00', end: '17:00' }
    };
    onChange(newHours);
  };

  const formatTimeForDisplay = (time: string): string => {
    if (time === 'closed') return 'Closed';
    
    const [hours, minutes] = time.split(':');
    const hour = parseInt(hours);
    const period = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    
    return `${displayHour}:${minutes} ${period}`;
  };

  const copyHours = (fromDay: string, toDay: string) => {
    const newHours = {
      ...businessHours,
      [toDay]: { ...businessHours[fromDay] }
    };
    onChange(newHours);
  };

  return (
    <div className="space-y-4">
      <div className="text-sm text-muted-foreground">
        Configure when your AI phone support is available. Calls outside business hours will receive an automated message.
      </div>
      
      <div className="space-y-3">
        {DAYS.map((day) => {
          const dayHours = businessHours[day.key];
          const isClosed = dayHours?.start === 'closed';
          
          return (
            <div key={day.key} className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center space-x-4">
                <div className="w-20 font-medium">
                  {day.label}
                </div>
                
                <Switch
                  checked={!isClosed}
                  onCheckedChange={(checked) => toggleDayClosed(day.key, !checked)}
                />
                
                <div className="text-sm text-muted-foreground">
                  {isClosed ? 'Closed' : 'Open'}
                </div>
              </div>
              
              {!isClosed && (
                <div className="flex items-center space-x-2">
                  <Select
                    value={dayHours?.start || '09:00'}
                    onValueChange={(value) => updateDayHours(day.key, 'start', value)}
                  >
                    <SelectTrigger className="w-24">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TIME_OPTIONS.map((time) => (
                        <SelectItem key={time} value={time}>
                          {formatTimeForDisplay(time)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  
                  <span className="text-muted-foreground">to</span>
                  
                  <Select
                    value={dayHours?.end || '17:00'}
                    onValueChange={(value) => updateDayHours(day.key, 'end', value)}
                  >
                    <SelectTrigger className="w-24">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TIME_OPTIONS.map((time) => (
                        <SelectItem key={time} value={time}>
                          {formatTimeForDisplay(time)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
          );
        })}
      </div>
      
      {/* Quick Actions */}
      <div className="flex flex-wrap gap-2 pt-2">
        <button
          type="button"
          className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
          onClick={() => {
            const standardHours = { start: '09:00', end: '17:00' };
            const newHours = { ...businessHours };
            ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'].forEach(day => {
              newHours[day] = standardHours;
            });
            onChange(newHours);
          }}
        >
          Set Standard Business Hours (M-F 9-5)
        </button>
        
        <button
          type="button"
          className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
          onClick={() => {
            const alwaysOpen = { start: '00:00', end: '23:59' };
            const newHours = { ...businessHours };
            DAYS.forEach(day => {
              newHours[day.key] = alwaysOpen;
            });
            onChange(newHours);
          }}
        >
          24/7 Operation
        </button>
        
        <button
          type="button"
          className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
          onClick={() => {
            const closedHours = { start: 'closed', end: 'closed' };
            const newHours = { ...businessHours };
            ['saturday', 'sunday'].forEach(day => {
              newHours[day] = closedHours;
            });
            onChange(newHours);
          }}
        >
          Close Weekends
        </button>
      </div>
    </div>
  );
};
