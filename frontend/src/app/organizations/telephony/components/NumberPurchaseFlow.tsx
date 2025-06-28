'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { telephonyService } from '@/services/telephony';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Phone, MapPin, DollarSign, Search, RefreshCw } from 'lucide-react';

export interface AvailableNumber {
  phoneNumber: string;
  friendlyName: string;
  locality: string;
  region: string;
  postalCode: string;
  isoCountry: string;
  phoneNumberType: 'local' | 'toll-free';
  capabilities: string[];
  monthlyFee: number;
}

interface NumberPurchaseFlowProps {
  onNumberSelected: (number: AvailableNumber) => void;
  onCancel: () => void;
  disabled?: boolean;
}

const POPULAR_AREA_CODES = [
  { code: '212', city: 'New York, NY' },
  { code: '310', city: 'Los Angeles, CA' },
  { code: '312', city: 'Chicago, IL' },
  { code: '415', city: 'San Francisco, CA' },
  { code: '617', city: 'Boston, MA' },
  { code: '713', city: 'Houston, TX' },
  { code: '202', city: 'Washington, DC' },
  { code: '305', city: 'Miami, FL' },
  { code: '404', city: 'Atlanta, GA' },
  { code: '206', city: 'Seattle, WA' }
];

export default function NumberPurchaseFlow({ onNumberSelected, onCancel, disabled = false }: NumberPurchaseFlowProps) {
  const { token } = useAuth();
  const [searchParams, setSearchParams] = useState({
    areaCode: '',
    numberType: 'local' as 'local' | 'toll-free',
    country: 'US'
  });
  const [availableNumbers, setAvailableNumbers] = useState<AvailableNumber[]>([]);
  const [selectedNumber, setSelectedNumber] = useState<AvailableNumber | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isPurchasing, setIsPurchasing] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async () => {
    if (!searchParams.areaCode && searchParams.numberType === 'local') {
      setSearchError('Please enter an area code for local numbers');
      return;
    }

    if (!token) {
      setSearchError('Authentication required. Please log in.');
      return;
    }

    setIsSearching(true);
    setSearchError(null);
    setHasSearched(true);

    try {
      const response = await telephonyService.searchAvailableNumbers(
        searchParams.areaCode,
        searchParams.numberType,
        searchParams.country,
        10,
        token
      );

      setAvailableNumbers(response.numbers || []);
    } catch (error: any) {
      console.error('Error searching numbers:', error);
      setSearchError(error.message || 'Failed to search for available numbers. Please try again.');
    } finally {
      setIsSearching(false);
    }
  };

  const handlePurchase = () => {
    if (!selectedNumber) return;
    onNumberSelected(selectedNumber);
  };

  return (
    <div className="space-y-6">
      {/* Search Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Search Available Numbers
          </CardTitle>
          <CardDescription>
            Find phone numbers available for purchase in your preferred area
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="numberType">Number Type</Label>
              <Select 
                value={searchParams.numberType} 
                onValueChange={(value: 'local' | 'toll-free') => 
                  setSearchParams(prev => ({ ...prev, numberType: value }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="local">
                    <div className="flex items-center justify-between w-full">
                      <span>Local Number</span>
                      <Badge variant="secondary">$1/month</Badge>
                    </div>
                  </SelectItem>
                  <SelectItem value="toll-free">
                    <div className="flex items-center justify-between w-full">
                      <span>Toll-Free Number</span>
                      <Badge variant="secondary">$15/month</Badge>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {searchParams.numberType === 'local' && (
              <div className="space-y-2">
                <Label htmlFor="areaCode">Area Code</Label>
                <Input
                  id="areaCode"
                  placeholder="e.g., 415"
                  value={searchParams.areaCode}
                  onChange={(e) => setSearchParams(prev => ({ 
                    ...prev, 
                    areaCode: e.target.value.replace(/\D/g, '').slice(0, 3)
                  }))}
                  maxLength={3}
                />
              </div>
            )}
          </div>

          {searchParams.numberType === 'local' && (
            <div className="space-y-2">
              <Label>Popular Area Codes</Label>
              <div className="flex flex-wrap gap-2">
                {POPULAR_AREA_CODES.map((area) => (
                  <Button
                    key={area.code}
                    variant="outline"
                    size="sm"
                    onClick={() => setSearchParams(prev => ({ ...prev, areaCode: area.code }))}
                    className="text-xs"
                  >
                    {area.code} - {area.city}
                  </Button>
                ))}
              </div>
            </div>
          )}

          <Button 
            onClick={handleSearch} 
            disabled={isSearching || disabled}
            className="w-full"
          >
            {isSearching ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Searching...
              </>
            ) : (
              <>
                <Search className="h-4 w-4 mr-2" />
                Search Available Numbers
              </>
            )}
          </Button>

          {searchError && (
            <Alert variant="destructive">
              <AlertDescription>{searchError}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Search Results */}
      {hasSearched && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Available Numbers</span>
              <Button variant="outline" size="sm" onClick={handleSearch} disabled={isSearching}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </CardTitle>
            <CardDescription>
              {availableNumbers.length > 0 ? 
                `Found ${availableNumbers.length} available numbers` : 
                'No numbers found for your search criteria'
              }
            </CardDescription>
          </CardHeader>
          <CardContent>
            {availableNumbers.length > 0 ? (
              <div className="space-y-3">
                {availableNumbers.map((number) => (
                  <Card 
                    key={number.phoneNumber} 
                    className={`cursor-pointer transition-all hover:shadow-md ${
                      selectedNumber?.phoneNumber === number.phoneNumber ? 
                      'ring-2 ring-primary border-primary' : ''
                    }`}
                    onClick={() => setSelectedNumber(number)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Phone className="h-5 w-5 text-primary" />
                          <div>
                            <p className="font-semibold">{number.friendlyName}</p>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <MapPin className="h-3 w-3" />
                              {number.locality}, {number.region}
                              <Badge variant="outline" className="ml-2">
                                {number.phoneNumberType}
                              </Badge>
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="flex items-center gap-1 text-lg font-semibold">
                            <DollarSign className="h-4 w-4" />
                            {number.monthlyFee}
                          </div>
                          <p className="text-xs text-muted-foreground">per month</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Phone className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No numbers available for the selected criteria.</p>
                <p className="text-sm">Try a different area code or number type.</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Purchase Actions */}
      {selectedNumber && (
        <div className="flex gap-3">
          <Button
            onClick={handlePurchase}
            disabled={isPurchasing || disabled}
            className="flex-1"
          >
            {isPurchasing ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Purchasing...
              </>
            ) : (
              <>
                Purchase {selectedNumber.friendlyName} (${selectedNumber.monthlyFee}/month)
              </>
            )}
          </Button>
          <Button variant="outline" onClick={onCancel} disabled={isPurchasing}>
            Cancel
          </Button>
        </div>
      )}
    </div>
  );
}