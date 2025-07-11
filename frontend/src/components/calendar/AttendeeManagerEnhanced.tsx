'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuCheckboxItem,
} from '@/components/ui/dropdown-menu';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Users, 
  UserPlus, 
  Mail, 
  Trash2, 
  Send, 
  CheckCircle, 
  XCircle, 
  Clock,
  AlertCircle,
  Building2,
  User,
  ChevronDown,
  Search,
  Check,
  UserCheck,
  ExternalLink
} from 'lucide-react';
import { 
  calendarService, 
  CalendarEventAttendee,
  CalendarEventAttendeeCreate,
  CalendarEventAttendeeList,
  AttendeeInvitationRequest
} from '@/services/calendar';
import { cn } from '@/lib/utils';

interface Contact {
  id: string;
  business_name: string;
  contact_name: string;
  contact_email?: string;
  phone?: string;
  city?: string;
  state?: string;
  status: string;
}

interface User {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  role: string;
}

interface AttendeeManagerProps {
  eventId?: string;
  isEventCreated: boolean;
  onAttendeesChange?: (attendees: CalendarEventAttendee[]) => void;
}

export function AttendeeManagerEnhanced({ eventId, isEventCreated, onAttendeesChange }: AttendeeManagerProps) {
  const [attendees, setAttendees] = useState<CalendarEventAttendee[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [contactsLoading, setContactsLoading] = useState(false);
  const [usersLoading, setUsersLoading] = useState(false);
  
  // Add attendee form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState<string[]>([]);
  const [selectedContacts, setSelectedContacts] = useState<string[]>([]);
  const [externalAttendees, setExternalAttendees] = useState<Array<{email: string; name: string}>>([]);
  const [externalEmail, setExternalEmail] = useState('');
  const [externalName, setExternalName] = useState('');
  const [contactSearch, setContactSearch] = useState('');
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [contactDropdownOpen, setContactDropdownOpen] = useState(false);
  
  // Invitation state
  const [showInviteForm, setShowInviteForm] = useState(false);
  const [selectedAttendees, setSelectedAttendees] = useState<string[]>([]);
  const [customMessage, setCustomMessage] = useState('');
  const [sendInvitations, setSendInvitations] = useState(true);

  useEffect(() => {
    if (isEventCreated && eventId) {
      loadAttendees();
    }
    loadContacts();
    loadUsers();
  }, [eventId, isEventCreated]);

  const loadAttendees = async () => {
    if (!eventId) return;
    
    try {
      setLoading(true);
      const attendeeList = await calendarService.listEventAttendees(eventId);
      setAttendees(attendeeList.attendees);
      onAttendeesChange?.(attendeeList.attendees);
    } catch (error) {
      console.error('Failed to load attendees:', error);
      setAttendees([]);
    } finally {
      setLoading(false);
    }
  };

  const loadContacts = async () => {
    try {
      setContactsLoading(true);
      
      const tokens = localStorage.getItem('tokens');
      let authHeader = '';
      if (tokens) {
        try {
          const parsedTokens = JSON.parse(tokens);
          if (parsedTokens.access_token) {
            authHeader = `Bearer ${parsedTokens.access_token}`;
          }
        } catch (error) {
          console.warn('Failed to parse tokens:', error);
        }
      }
      
      const response = await fetch('/api/crm/contacts?limit=1000', {
        headers: {
          'Authorization': authHeader,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setContacts(data.contacts || []);
      } else {
        console.error('Failed to load contacts:', response.status, response.statusText);
        setContacts([]);
      }
    } catch (error) {
      console.error('Failed to load contacts:', error);
      setContacts([]);
    } finally {
      setContactsLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      setUsersLoading(true);
      
      const tokens = localStorage.getItem('tokens');
      let authHeader = '';
      if (tokens) {
        try {
          const parsedTokens = JSON.parse(tokens);
          if (parsedTokens.access_token) {
            authHeader = `Bearer ${parsedTokens.access_token}`;
          }
        } catch (error) {
          console.warn('Failed to parse tokens:', error);
        }
      }
      
      const response = await fetch('/api/users', {
        headers: {
          'Authorization': authHeader,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setUsers(data.users || []);
      } else {
        console.error('Failed to load users:', response.status, response.statusText);
        setUsers([]);
      }
    } catch (error) {
      console.error('Failed to load users:', error);
      setUsers([]);
    } finally {
      setUsersLoading(false);
    }
  };

  const handleAddAttendees = async () => {
    if (!eventId) return;

    try {
      setLoading(true);
      
      // Add selected users
      for (const userId of selectedUsers) {
        const attendeeData: CalendarEventAttendeeCreate = {
          attendee_type: 'user',
          user_id: userId,
        };
        await calendarService.addEventAttendee(eventId, attendeeData);
      }
      
      // Add selected contacts
      for (const contactId of selectedContacts) {
        const attendeeData: CalendarEventAttendeeCreate = {
          attendee_type: 'contact',
          contact_id: contactId,
        };
        await calendarService.addEventAttendee(eventId, attendeeData);
      }
      
      // Add external attendees
      for (const external of externalAttendees) {
        const attendeeData: CalendarEventAttendeeCreate = {
          attendee_type: 'external',
          external_email: external.email,
          external_name: external.name,
        };
        await calendarService.addEventAttendee(eventId, attendeeData);
      }
      
      await loadAttendees();
      
      // Reset form
      setShowAddForm(false);
      setSelectedUsers([]);
      setSelectedContacts([]);
      setExternalAttendees([]);
      setExternalEmail('');
      setExternalName('');
      setContactSearch('');
    } catch (error) {
      console.error('Failed to add attendees:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddExternalAttendee = () => {
    if (externalEmail && externalName) {
      setExternalAttendees([...externalAttendees, { email: externalEmail, name: externalName }]);
      setExternalEmail('');
      setExternalName('');
    }
  };

  const handleRemoveExternalAttendee = (index: number) => {
    setExternalAttendees(externalAttendees.filter((_, i) => i !== index));
  };

  const handleRemoveAttendee = async (attendeeId: string) => {
    if (!eventId) return;

    try {
      setLoading(true);
      await calendarService.removeEventAttendee(eventId, attendeeId);
      await loadAttendees();
    } catch (error) {
      console.error('Failed to remove attendee:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSendInvitations = async () => {
    if (!eventId || selectedAttendees.length === 0) return;

    const invitationRequest: AttendeeInvitationRequest = {
      attendee_ids: selectedAttendees,
      send_invitations: sendInvitations,
      custom_message: customMessage || undefined,
    };

    try {
      setLoading(true);
      const result = await calendarService.sendEventInvitations(eventId, invitationRequest);
      console.log('Invitations sent:', result);
      await loadAttendees();
      
      // Reset form
      setShowInviteForm(false);
      setSelectedAttendees([]);
      setCustomMessage('');
    } catch (error) {
      console.error('Failed to send invitations:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredContacts = contacts.filter(contact =>
    contact.business_name.toLowerCase().includes(contactSearch.toLowerCase()) ||
    contact.contact_name.toLowerCase().includes(contactSearch.toLowerCase()) ||
    (contact.contact_email && contact.contact_email.toLowerCase().includes(contactSearch.toLowerCase()))
  );

  const getAttendeeStatusBadge = (attendee: CalendarEventAttendee) => {
    const statusConfig = {
      'accepted': { color: 'bg-green-100 text-green-800', icon: CheckCircle },
      'declined': { color: 'bg-red-100 text-red-800', icon: XCircle },
      'tentative': { color: 'bg-yellow-100 text-yellow-800', icon: Clock },
      'no_response': { color: 'bg-gray-100 text-gray-800', icon: AlertCircle },
    };

    const config = statusConfig[attendee.response_status as keyof typeof statusConfig];
    const Icon = config?.icon || AlertCircle;

    return (
      <Badge className={`${config?.color} flex items-center gap-1`}>
        <Icon className="h-3 w-3" />
        {attendee.response_status.replace('_', ' ')}
      </Badge>
    );
  };

  const getInvitationStatusBadge = (status: string) => {
    const statusConfig = {
      'sent': { color: 'bg-blue-100 text-blue-800', text: 'Sent' },
      'pending': { color: 'bg-gray-100 text-gray-800', text: 'Pending' },
      'failed': { color: 'bg-red-100 text-red-800', text: 'Failed' },
      'delivered': { color: 'bg-green-100 text-green-800', text: 'Delivered' },
    };

    const config = statusConfig[status as keyof typeof statusConfig] || { color: 'bg-gray-100 text-gray-800', text: status };

    return (
      <Badge className={config.color}>
        {config.text}
      </Badge>
    );
  };

  const totalSelectedCount = selectedUsers.length + selectedContacts.length + externalAttendees.length;

  if (!isEventCreated) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5" />
          <Label className="text-base font-medium">Event Attendees</Label>
        </div>
        <div className="p-4 border border-dashed rounded-lg text-center text-gray-500">
          <Users className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>Save the event first to manage attendees</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5" />
          <Label className="text-base font-medium">Event Attendees</Label>
          <Badge variant="outline">{attendees.length}</Badge>
        </div>
        
        <div className="flex gap-2">
          {attendees.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowInviteForm(!showInviteForm)}
              disabled={loading}
            >
              <Send className="h-4 w-4 mr-2" />
              Send Invites
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowAddForm(!showAddForm)}
            disabled={loading}
          >
            <UserPlus className="h-4 w-4 mr-2" />
            Add Attendees
          </Button>
        </div>
      </div>

      {/* Attendee List */}
      {attendees.length > 0 ? (
        <div className="space-y-2">
          {attendees.map((attendee) => (
            <div key={attendee.id} className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex items-center gap-3">
                {attendee.attendee_type === 'user' && <User className="h-4 w-4 text-blue-600" />}
                {attendee.attendee_type === 'contact' && <Building2 className="h-4 w-4 text-green-600" />}
                {attendee.attendee_type === 'external' && <Mail className="h-4 w-4 text-purple-600" />}
                
                <div>
                  <p className="font-medium">{attendee.attendee_name || 'Unknown'}</p>
                  <p className="text-sm text-gray-600">{attendee.attendee_email}</p>
                  <div className="flex items-center gap-2 mt-1">
                    {getAttendeeStatusBadge(attendee)}
                    {getInvitationStatusBadge(attendee.invitation_status)}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <Checkbox
                  checked={selectedAttendees.includes(attendee.id)}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setSelectedAttendees([...selectedAttendees, attendee.id]);
                    } else {
                      setSelectedAttendees(selectedAttendees.filter(id => id !== attendee.id));
                    }
                  }}
                />
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRemoveAttendee(attendee.id)}
                  disabled={loading}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-4 border border-dashed rounded-lg text-center text-gray-500">
          <Users className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>No attendees added yet</p>
        </div>
      )}

      {/* Add Attendee Form */}
      {showAddForm && (
        <div className="p-4 border rounded-lg space-y-4 bg-gray-50">
          <div className="flex items-center justify-between">
            <h4 className="font-medium">Add Attendees</h4>
            {totalSelectedCount > 0 && (
              <Badge variant="secondary">
                {totalSelectedCount} selected
              </Badge>
            )}
          </div>
          
          <Tabs defaultValue="internal" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="internal">
                <User className="h-4 w-4 mr-2" />
                Internal ({selectedUsers.length})
              </TabsTrigger>
              <TabsTrigger value="contacts">
                <Building2 className="h-4 w-4 mr-2" />
                Contacts ({selectedContacts.length})
              </TabsTrigger>
              <TabsTrigger value="external">
                <ExternalLink className="h-4 w-4 mr-2" />
                External ({externalAttendees.length})
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="internal" className="space-y-4">
              <div>
                <Label className="text-sm text-gray-600 mb-2">
                  Select team members from your organization
                </Label>
                <DropdownMenu open={userDropdownOpen} onOpenChange={setUserDropdownOpen}>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="w-full justify-between">
                      {selectedUsers.length > 0 
                        ? `${selectedUsers.length} team members selected` 
                        : 'Select team members'}
                      <ChevronDown className="h-4 w-4 opacity-50" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent className="w-full" align="start">
                    <DropdownMenuLabel>Team Members</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <ScrollArea className="h-[300px]">
                      {usersLoading ? (
                        <div className="p-4 text-center text-sm text-gray-500">
                          Loading team members...
                        </div>
                      ) : users.length === 0 ? (
                        <div className="p-4 text-center text-sm text-gray-500">
                          No team members found
                        </div>
                      ) : (
                        <>
                          {users.map((user) => (
                            <DropdownMenuCheckboxItem
                              key={user.id}
                              checked={selectedUsers.includes(user.id)}
                              onCheckedChange={(checked) => {
                                if (checked) {
                                  setSelectedUsers([...selectedUsers, user.id]);
                                } else {
                                  setSelectedUsers(selectedUsers.filter(id => id !== user.id));
                                }
                              }}
                            >
                              <div className="flex items-center justify-between w-full">
                                <div>
                                  <p className="font-medium">{user.first_name} {user.last_name}</p>
                                  <p className="text-xs text-gray-500">{user.email}</p>
                                </div>
                                <Badge variant="outline" className="text-xs ml-2">
                                  {user.role}
                                </Badge>
                              </div>
                            </DropdownMenuCheckboxItem>
                          ))}
                        </>
                      )}
                    </ScrollArea>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
              
              {selectedUsers.length > 0 && (
                <div className="space-y-2">
                  <Label className="text-sm">Selected Team Members:</Label>
                  <div className="flex flex-wrap gap-2">
                    {selectedUsers.map(userId => {
                      const user = users.find(u => u.id === userId);
                      return user ? (
                        <Badge key={userId} variant="secondary" className="flex items-center gap-1">
                          <UserCheck className="h-3 w-3" />
                          {user.first_name} {user.last_name}
                          <button
                            onClick={() => setSelectedUsers(selectedUsers.filter(id => id !== userId))}
                            className="ml-1 hover:text-red-600"
                          >
                            ×
                          </button>
                        </Badge>
                      ) : null;
                    })}
                  </div>
                </div>
              )}
            </TabsContent>
            
            <TabsContent value="contacts" className="space-y-4">
              <div>
                <Label className="text-sm text-gray-600 mb-2">
                  Search and select from your CRM contacts
                </Label>
                <Popover open={contactDropdownOpen} onOpenChange={setContactDropdownOpen}>
                  <PopoverTrigger asChild>
                    <Button variant="outline" className="w-full justify-between">
                      {selectedContacts.length > 0 
                        ? `${selectedContacts.length} contacts selected` 
                        : 'Search contacts'}
                      <Search className="h-4 w-4 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-full p-0" align="start">
                    <Command>
                      <CommandInput 
                        placeholder="Search contacts..." 
                        value={contactSearch}
                        onValueChange={setContactSearch}
                      />
                      <CommandList>
                        <CommandEmpty>No contacts found.</CommandEmpty>
                        <CommandGroup>
                          <ScrollArea className="h-[300px]">
                            {contactsLoading ? (
                              <div className="p-4 text-center text-sm text-gray-500">
                                Loading contacts...
                              </div>
                            ) : (
                              <>
                                {filteredContacts.slice(0, 50).map((contact) => (
                                  <CommandItem
                                    key={contact.id}
                                    onSelect={() => {
                                      if (selectedContacts.includes(contact.id)) {
                                        setSelectedContacts(selectedContacts.filter(id => id !== contact.id));
                                      } else {
                                        setSelectedContacts([...selectedContacts, contact.id]);
                                      }
                                    }}
                                  >
                                    <div className="flex items-center justify-between w-full">
                                      <div className="flex items-center gap-2">
                                        <Checkbox
                                          checked={selectedContacts.includes(contact.id)}
                                          onCheckedChange={(checked) => {
                                            if (checked) {
                                              setSelectedContacts([...selectedContacts, contact.id]);
                                            } else {
                                              setSelectedContacts(selectedContacts.filter(id => id !== contact.id));
                                            }
                                          }}
                                        />
                                        <div>
                                          <p className="font-medium">{contact.business_name}</p>
                                          <p className="text-xs text-gray-500">{contact.contact_name}</p>
                                          {contact.contact_email && (
                                            <p className="text-xs text-gray-400">{contact.contact_email}</p>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  </CommandItem>
                                ))}
                              </>
                            )}
                          </ScrollArea>
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
              </div>
              
              {selectedContacts.length > 0 && (
                <div className="space-y-2">
                  <Label className="text-sm">Selected Contacts:</Label>
                  <div className="flex flex-wrap gap-2">
                    {selectedContacts.map(contactId => {
                      const contact = contacts.find(c => c.id === contactId);
                      return contact ? (
                        <Badge key={contactId} variant="secondary" className="flex items-center gap-1">
                          <Building2 className="h-3 w-3" />
                          {contact.business_name}
                          <button
                            onClick={() => setSelectedContacts(selectedContacts.filter(id => id !== contactId))}
                            className="ml-1 hover:text-red-600"
                          >
                            ×
                          </button>
                        </Badge>
                      ) : null;
                    })}
                  </div>
                </div>
              )}
            </TabsContent>
            
            <TabsContent value="external" className="space-y-4">
              <div>
                <Label className="text-sm text-gray-600 mb-2">
                  Add external attendees by email
                </Label>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">Name</Label>
                    <Input
                      value={externalName}
                      onChange={(e) => setExternalName(e.target.value)}
                      placeholder="John Doe"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Email</Label>
                    <div className="flex gap-2">
                      <Input
                        type="email"
                        value={externalEmail}
                        onChange={(e) => setExternalEmail(e.target.value)}
                        placeholder="john@example.com"
                        onKeyPress={(e) => {
                          if (e.key === 'Enter') {
                            handleAddExternalAttendee();
                          }
                        }}
                      />
                      <Button
                        size="sm"
                        onClick={handleAddExternalAttendee}
                        disabled={!externalEmail || !externalName}
                      >
                        Add
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
              
              {externalAttendees.length > 0 && (
                <div className="space-y-2">
                  <Label className="text-sm">External Attendees:</Label>
                  <div className="space-y-2">
                    {externalAttendees.map((attendee, index) => (
                      <div key={index} className="flex items-center justify-between p-2 border rounded">
                        <div>
                          <p className="font-medium text-sm">{attendee.name}</p>
                          <p className="text-xs text-gray-500">{attendee.email}</p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveExternalAttendee(index)}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>

          <Separator />

          <div className="flex gap-2">
            <Button
              onClick={handleAddAttendees}
              disabled={loading || totalSelectedCount === 0}
            >
              Add {totalSelectedCount} Attendee{totalSelectedCount !== 1 ? 's' : ''}
            </Button>
            <Button 
              variant="outline" 
              onClick={() => {
                setShowAddForm(false);
                setSelectedUsers([]);
                setSelectedContacts([]);
                setExternalAttendees([]);
                setContactSearch('');
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Send Invitations Form */}
      {showInviteForm && (
        <div className="p-4 border rounded-lg space-y-4 bg-blue-50">
          <h4 className="font-medium">Send Invitations</h4>
          
          <div className="flex items-center space-x-2">
            <Checkbox
              id="send-invitations"
              checked={sendInvitations}
              onCheckedChange={(checked) => setSendInvitations(!!checked)}
            />
            <Label htmlFor="send-invitations">Send email invitations</Label>
          </div>

          <div>
            <Label>Custom Message (Optional)</Label>
            <Textarea
              value={customMessage}
              onChange={(e) => setCustomMessage(e.target.value)}
              placeholder="Add a personal message to the invitation..."
              rows={3}
            />
          </div>

          <div>
            <p className="text-sm text-gray-600">
              {selectedAttendees.length > 0 
                ? `${selectedAttendees.length} attendee(s) selected`
                : 'Select attendees above to send invitations'
              }
            </p>
          </div>

          <div className="flex gap-2">
            <Button
              onClick={handleSendInvitations}
              disabled={loading || selectedAttendees.length === 0}
            >
              <Send className="h-4 w-4 mr-2" />
              Send Invitations
            </Button>
            <Button variant="outline" onClick={() => setShowInviteForm(false)}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}