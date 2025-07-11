'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
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
  User
} from 'lucide-react';
import { 
  calendarService, 
  CalendarEventAttendee,
  CalendarEventAttendeeCreate,
  CalendarEventAttendeeList,
  AttendeeInvitationRequest
} from '@/services/calendar';

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

export function AttendeeManager({ eventId, isEventCreated, onAttendeesChange }: AttendeeManagerProps) {
  const [attendees, setAttendees] = useState<CalendarEventAttendee[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [contactsLoading, setContactsLoading] = useState(false);
  const [usersLoading, setUsersLoading] = useState(false);
  
  // Add attendee form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [attendeeType, setAttendeeType] = useState<'user' | 'contact' | 'external'>('contact');
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedContactId, setSelectedContactId] = useState('');
  const [externalEmail, setExternalEmail] = useState('');
  const [externalName, setExternalName] = useState('');
  const [contactSearch, setContactSearch] = useState('');
  const [userSearch, setUserSearch] = useState('');
  
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
      // Don't block the UI if attendees fail to load
      setAttendees([]);
    } finally {
      setLoading(false);
    }
  };

  const loadContacts = async () => {
    try {
      setContactsLoading(true);
      
      // Get tokens from localStorage in the correct format
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
      
      // Get tokens from localStorage in the correct format
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

  const handleAddAttendee = async () => {
    if (!eventId) return;

    const attendeeData: CalendarEventAttendeeCreate = {
      attendee_type: attendeeType,
      user_id: attendeeType === 'user' ? selectedUserId : undefined,
      contact_id: attendeeType === 'contact' ? selectedContactId : undefined,
      external_email: attendeeType === 'external' ? externalEmail : undefined,
      external_name: attendeeType === 'external' ? externalName : undefined,
    };

    try {
      setLoading(true);
      await calendarService.addEventAttendee(eventId, attendeeData);
      await loadAttendees();
      
      // Reset form
      setShowAddForm(false);
      setSelectedUserId('');
      setSelectedContactId('');
      setExternalEmail('');
      setExternalName('');
      setContactSearch('');
      setUserSearch('');
    } catch (error) {
      console.error('Failed to add attendee:', error);
    } finally {
      setLoading(false);
    }
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

  const filteredUsers = users.filter(user =>
    `${user.first_name} ${user.last_name}`.toLowerCase().includes(userSearch.toLowerCase()) ||
    user.email.toLowerCase().includes(userSearch.toLowerCase())
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
            Add Attendee
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
          <h4 className="font-medium">Add Attendee</h4>
          
          <div>
            <Label>Attendee Type</Label>
            <Select value={attendeeType} onValueChange={(value: any) => setAttendeeType(value)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="contact">CRM Contact</SelectItem>
                <SelectItem value="user">Team Member</SelectItem>
                <SelectItem value="external">External Person</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {attendeeType === 'contact' && (
            <div className="space-y-2">
              <Label>Select Contact</Label>
              <Input
                placeholder="Search contacts..."
                value={contactSearch}
                onChange={(e) => setContactSearch(e.target.value)}
              />
              {contactsLoading ? (
                <p className="text-sm text-gray-500">Loading contacts...</p>
              ) : filteredContacts.length > 0 ? (
                <div className="max-h-40 overflow-y-auto border rounded-lg">
                  {filteredContacts.slice(0, 10).map((contact) => (
                    <div
                      key={contact.id}
                      className={`p-2 hover:bg-gray-50 cursor-pointer border-b last:border-b-0 ${
                        selectedContactId === contact.id ? 'bg-blue-50' : ''
                      }`}
                      onClick={() => setSelectedContactId(contact.id)}
                    >
                      <div>
                        <p className="font-medium text-sm">{contact.business_name}</p>
                        <p className="text-xs text-gray-600">{contact.contact_name}</p>
                        {contact.contact_email && (
                          <p className="text-xs text-gray-500">{contact.contact_email}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : contactSearch ? (
                <p className="text-sm text-gray-500">No contacts found</p>
              ) : null}
            </div>
          )}

          {attendeeType === 'user' && (
            <div className="space-y-2">
              <Label>Select Team Member</Label>
              <Input
                placeholder="Search team members..."
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
              />
              {usersLoading ? (
                <p className="text-sm text-gray-500">Loading team members...</p>
              ) : filteredUsers.length > 0 ? (
                <div className="max-h-40 overflow-y-auto border rounded-lg">
                  {filteredUsers.slice(0, 10).map((user) => (
                    <div
                      key={user.id}
                      className={`p-2 hover:bg-gray-50 cursor-pointer border-b last:border-b-0 ${
                        selectedUserId === user.id ? 'bg-blue-50' : ''
                      }`}
                      onClick={() => setSelectedUserId(user.id)}
                    >
                      <div>
                        <p className="font-medium text-sm">{user.first_name} {user.last_name}</p>
                        <p className="text-xs text-gray-600">{user.email}</p>
                        <Badge variant="outline" className="text-xs">{user.role}</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              ) : userSearch ? (
                <p className="text-sm text-gray-500">No team members found</p>
              ) : null}
            </div>
          )}

          {attendeeType === 'external' && (
            <div className="space-y-2">
              <div>
                <Label>Name</Label>
                <Input
                  value={externalName}
                  onChange={(e) => setExternalName(e.target.value)}
                  placeholder="Enter attendee name"
                />
              </div>
              <div>
                <Label>Email</Label>
                <Input
                  type="email"
                  value={externalEmail}
                  onChange={(e) => setExternalEmail(e.target.value)}
                  placeholder="Enter email address"
                />
              </div>
            </div>
          )}

          <div className="flex gap-2">
            <Button
              onClick={handleAddAttendee}
              disabled={
                loading ||
                (attendeeType === 'contact' && !selectedContactId) ||
                (attendeeType === 'user' && !selectedUserId) ||
                (attendeeType === 'external' && (!externalEmail || !externalName))
              }
            >
              Add Attendee
            </Button>
            <Button variant="outline" onClick={() => setShowAddForm(false)}>
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