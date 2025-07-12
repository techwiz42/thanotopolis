import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const authorization = request.headers.get('authorization');
    
    if (!authorization) {
      return NextResponse.json(
        { detail: 'Authorization header required' },
        { status: 401 }
      );
    }

    // Forward all query parameters to the backend search endpoint
    const queryString = searchParams.toString();
    const url = `${BACKEND_URL}/crm/contacts/search${queryString ? `?${queryString}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': authorization,
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();
    
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error proxying contacts search request:', error);
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}