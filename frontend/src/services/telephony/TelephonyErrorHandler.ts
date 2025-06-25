// src/services/telephony/TelephonyErrorHandler.ts
import { EventEmitter } from 'events';

export enum TelephonyErrorType {
  CONNECTION = 'connection',
  AUDIO = 'audio',
  TTS = 'tts',
  STT = 'stt',
  CALL_MANAGEMENT = 'call_management',
  TWILIO = 'twilio',
  AUTHENTICATION = 'authentication',
  CONFIGURATION = 'configuration',
  NETWORK = 'network',
  TIMEOUT = 'timeout',
  UNKNOWN = 'unknown'
}

export enum TelephonyErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

export interface TelephonyError {
  id: string;
  type: TelephonyErrorType;
  severity: TelephonyErrorSeverity;
  message: string;
  details?: Record<string, any>;
  callId?: string;
  component: string;
  timestamp: Date;
  stack?: string;
  resolved: boolean;
  resolvedAt?: Date;
  resolutionNotes?: string;
}

export interface TelephonyLogEntry {
  id: string;
  level: 'debug' | 'info' | 'warn' | 'error';
  message: string;
  context: Record<string, any>;
  callId?: string;
  component: string;
  timestamp: Date;
}

/**
 * Centralized error handling and logging for telephony system
 * Provides debugging, monitoring, and error recovery capabilities
 */
export class TelephonyErrorHandler extends EventEmitter {
  private errors: Map<string, TelephonyError> = new Map();
  private logs: TelephonyLogEntry[] = [];
  private maxLogEntries = 1000;
  private maxErrors = 500;
  private isDebugMode = false;

  constructor() {
    super();
    this.isDebugMode = process.env.NODE_ENV === 'development';
  }

  /**
   * Log an error in the telephony system
   */
  logError(
    type: TelephonyErrorType,
    message: string,
    component: string,
    options: {
      severity?: TelephonyErrorSeverity;
      details?: Record<string, any>;
      callId?: string;
      error?: Error;
    } = {}
  ): string {
    const {
      severity = TelephonyErrorSeverity.MEDIUM,
      details = {},
      callId,
      error
    } = options;

    const errorId = `err-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    const telephonyError: TelephonyError = {
      id: errorId,
      type,
      severity,
      message,
      details,
      callId,
      component,
      timestamp: new Date(),
      stack: error?.stack,
      resolved: false
    };

    this.errors.set(errorId, telephonyError);

    // Log to console with appropriate level
    const logLevel = this.getLogLevelForSeverity(severity);
    const logMessage = `📞 [${component}] ${message}`;
    const logContext = {
      errorId,
      type,
      severity,
      callId,
      details,
      stack: error?.stack
    };

    this.log(logLevel, logMessage, component, logContext, callId);

    // Emit error event
    this.emit('error', telephonyError);

    // Auto-resolve low severity errors after 5 minutes
    if (severity === TelephonyErrorSeverity.LOW) {
      setTimeout(() => {
        this.resolveError(errorId, 'Auto-resolved after timeout');
      }, 5 * 60 * 1000);
    }

    // Clean up old errors if we have too many
    if (this.errors.size > this.maxErrors) {
      this.cleanupOldErrors();
    }

    return errorId;
  }

  /**
   * Log a general message
   */
  log(
    level: 'debug' | 'info' | 'warn' | 'error',
    message: string,
    component: string,
    context: Record<string, any> = {},
    callId?: string
  ): void {
    const logEntry: TelephonyLogEntry = {
      id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      level,
      message,
      context,
      callId,
      component,
      timestamp: new Date()
    };

    this.logs.push(logEntry);

    // Console logging with appropriate level
    const consoleMessage = `📞 [${component}${callId ? `:${callId}` : ''}] ${message}`;
    
    switch (level) {
      case 'debug':
        if (this.isDebugMode) {
          console.debug(consoleMessage, context);
        }
        break;
      case 'info':
        console.info(consoleMessage, context);
        break;
      case 'warn':
        console.warn(consoleMessage, context);
        break;
      case 'error':
        console.error(consoleMessage, context);
        break;
    }

    // Emit log event
    this.emit('log', logEntry);

    // Clean up old logs if we have too many
    if (this.logs.length > this.maxLogEntries) {
      this.logs = this.logs.slice(-this.maxLogEntries + 100); // Keep latest entries
    }
  }

  /**
   * Resolve an error
   */
  resolveError(errorId: string, notes?: string): boolean {
    const error = this.errors.get(errorId);
    if (!error || error.resolved) {
      return false;
    }

    error.resolved = true;
    error.resolvedAt = new Date();
    error.resolutionNotes = notes;

    this.log('info', `Error resolved: ${error.message}`, error.component, {
      errorId,
      resolutionNotes: notes
    }, error.callId);

    this.emit('error_resolved', error);
    return true;
  }

  /**
   * Get errors by various filters
   */
  getErrors(filters: {
    type?: TelephonyErrorType;
    severity?: TelephonyErrorSeverity;
    callId?: string;
    component?: string;
    resolved?: boolean;
    since?: Date;
  } = {}): TelephonyError[] {
    let filteredErrors = Array.from(this.errors.values());

    if (filters.type) {
      filteredErrors = filteredErrors.filter(err => err.type === filters.type);
    }

    if (filters.severity) {
      filteredErrors = filteredErrors.filter(err => err.severity === filters.severity);
    }

    if (filters.callId) {
      filteredErrors = filteredErrors.filter(err => err.callId === filters.callId);
    }

    if (filters.component) {
      filteredErrors = filteredErrors.filter(err => err.component === filters.component);
    }

    if (filters.resolved !== undefined) {
      filteredErrors = filteredErrors.filter(err => err.resolved === filters.resolved);
    }

    if (filters.since) {
      filteredErrors = filteredErrors.filter(err => err.timestamp >= filters.since!);
    }

    return filteredErrors.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }

  /**
   * Get logs by various filters
   */
  getLogs(filters: {
    level?: 'debug' | 'info' | 'warn' | 'error';
    callId?: string;
    component?: string;
    since?: Date;
    limit?: number;
  } = {}): TelephonyLogEntry[] {
    let filteredLogs = [...this.logs];

    if (filters.level) {
      filteredLogs = filteredLogs.filter(log => log.level === filters.level);
    }

    if (filters.callId) {
      filteredLogs = filteredLogs.filter(log => log.callId === filters.callId);
    }

    if (filters.component) {
      filteredLogs = filteredLogs.filter(log => log.component === filters.component);
    }

    if (filters.since) {
      filteredLogs = filteredLogs.filter(log => log.timestamp >= filters.since!);
    }

    // Sort by timestamp (newest first)
    filteredLogs.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());

    // Apply limit
    if (filters.limit) {
      filteredLogs = filteredLogs.slice(0, filters.limit);
    }

    return filteredLogs;
  }

  /**
   * Get error statistics
   */
  getErrorStats(): {
    total: number;
    byType: Record<TelephonyErrorType, number>;
    bySeverity: Record<TelephonyErrorSeverity, number>;
    resolved: number;
    unresolved: number;
    last24Hours: number;
  } {
    const errors = Array.from(this.errors.values());
    const last24Hours = new Date(Date.now() - 24 * 60 * 60 * 1000);

    const stats = {
      total: errors.length,
      byType: {} as Record<TelephonyErrorType, number>,
      bySeverity: {} as Record<TelephonyErrorSeverity, number>,
      resolved: errors.filter(err => err.resolved).length,
      unresolved: errors.filter(err => !err.resolved).length,
      last24Hours: errors.filter(err => err.timestamp >= last24Hours).length
    };

    // Initialize counts
    Object.values(TelephonyErrorType).forEach(type => {
      stats.byType[type] = 0;
    });
    Object.values(TelephonyErrorSeverity).forEach(severity => {
      stats.bySeverity[severity] = 0;
    });

    // Count by type and severity
    errors.forEach(error => {
      stats.byType[error.type]++;
      stats.bySeverity[error.severity]++;
    });

    return stats;
  }

  /**
   * Export logs and errors for debugging
   */
  exportDiagnostics(callId?: string): {
    errors: TelephonyError[];
    logs: TelephonyLogEntry[];
    stats: {
      total: number;
      byType: Record<TelephonyErrorType, number>;
      bySeverity: Record<TelephonyErrorSeverity, number>;
      resolved: number;
      unresolved: number;
      last24Hours: number;
    };
    exported_at: string;
    call_id?: string;
  } {
    const filters = callId ? { callId } : {};
    
    return {
      errors: this.getErrors(filters),
      logs: this.getLogs(filters),
      stats: this.getErrorStats(),
      exported_at: new Date().toISOString(),
      call_id: callId
    };
  }

  /**
   * Handle common telephony error patterns
   */
  handleCommonErrors = {
    connectionTimeout: (component: string, callId?: string) => {
      return this.logError(
        TelephonyErrorType.TIMEOUT,
        'Connection timeout - network or service unavailable',
        component,
        {
          severity: TelephonyErrorSeverity.HIGH,
          callId,
          details: { 
            suggestion: 'Check network connectivity and backend service status',
            autoRetry: true
          }
        }
      );
    },

    authenticationFailed: (component: string, details: Record<string, any> = {}) => {
      return this.logError(
        TelephonyErrorType.AUTHENTICATION,
        'Authentication failed - invalid token or expired session',
        component,
        {
          severity: TelephonyErrorSeverity.HIGH,
          details: {
            ...details,
            suggestion: 'Refresh authentication token or re-login'
          }
        }
      );
    },

    audioStreamError: (component: string, callId: string, error: Error) => {
      return this.logError(
        TelephonyErrorType.AUDIO,
        'Audio stream error - unable to process audio data',
        component,
        {
          severity: TelephonyErrorSeverity.MEDIUM,
          callId,
          error,
          details: {
            suggestion: 'Check microphone permissions and audio device connectivity'
          }
        }
      );
    },

    ttsFailure: (component: string, callId: string, text: string, error: Error) => {
      return this.logError(
        TelephonyErrorType.TTS,
        'TTS synthesis failed - unable to generate speech',
        component,
        {
          severity: TelephonyErrorSeverity.MEDIUM,
          callId,
          error,
          details: {
            textLength: text.length,
            textPreview: text.substring(0, 100),
            suggestion: 'Check TTS service availability and text content'
          }
        }
      );
    },

    sttFailure: (component: string, callId: string, error: Error) => {
      return this.logError(
        TelephonyErrorType.STT,
        'STT transcription failed - unable to process speech',
        component,
        {
          severity: TelephonyErrorSeverity.MEDIUM,
          callId,
          error,
          details: {
            suggestion: 'Check STT service availability and audio quality'
          }
        }
      );
    },

    twilioError: (component: string, callId: string, error: Error, twilioDetails: Record<string, any> = {}) => {
      return this.logError(
        TelephonyErrorType.TWILIO,
        'Twilio service error - communication with phone service failed',
        component,
        {
          severity: TelephonyErrorSeverity.HIGH,
          callId,
          error,
          details: {
            ...twilioDetails,
            suggestion: 'Check Twilio service status and configuration'
          }
        }
      );
    }
  };

  /**
   * Get log level for error severity
   */
  private getLogLevelForSeverity(severity: TelephonyErrorSeverity): 'debug' | 'info' | 'warn' | 'error' {
    switch (severity) {
      case TelephonyErrorSeverity.LOW:
        return 'info';
      case TelephonyErrorSeverity.MEDIUM:
        return 'warn';
      case TelephonyErrorSeverity.HIGH:
      case TelephonyErrorSeverity.CRITICAL:
        return 'error';
    }
  }

  /**
   * Clean up old errors (keep only recent critical and high severity errors)
   */
  private cleanupOldErrors(): void {
    const cutoffTime = Date.now() - (7 * 24 * 60 * 60 * 1000); // 7 days ago
    const errors = Array.from(this.errors.entries());
    
    const toKeep = errors.filter(([_, error]) => {
      // Keep recent errors
      if (error.timestamp.getTime() > cutoffTime) return true;
      
      // Keep unresolved critical/high severity errors
      if (!error.resolved && 
          (error.severity === TelephonyErrorSeverity.CRITICAL || 
           error.severity === TelephonyErrorSeverity.HIGH)) {
        return true;
      }
      
      return false;
    });

    this.errors.clear();
    toKeep.forEach(([id, error]) => {
      this.errors.set(id, error);
    });

    this.log('info', `Cleaned up old errors, kept ${toKeep.length} recent/important errors`, 'TelephonyErrorHandler');
  }

  /**
   * Enable/disable debug mode
   */
  setDebugMode(enabled: boolean): void {
    this.isDebugMode = enabled;
    this.log('info', `Debug mode ${enabled ? 'enabled' : 'disabled'}`, 'TelephonyErrorHandler');
  }

  /**
   * Clear all logs and errors (for testing/reset)
   */
  clearAll(): void {
    this.errors.clear();
    this.logs = [];
    this.log('warn', 'All telephony logs and errors cleared', 'TelephonyErrorHandler');
  }

  /**
   * Get health status of telephony system
   */
  getHealthStatus(): {
    status: 'healthy' | 'degraded' | 'unhealthy';
    criticalErrors: number;
    highErrors: number;
    recentErrors: number;
    details: string[];
  } {
    const now = new Date();
    const last10Minutes = new Date(now.getTime() - 10 * 60 * 1000);
    const errors = Array.from(this.errors.values());

    const criticalErrors = errors.filter(err => 
      !err.resolved && err.severity === TelephonyErrorSeverity.CRITICAL
    ).length;

    const highErrors = errors.filter(err => 
      !err.resolved && err.severity === TelephonyErrorSeverity.HIGH
    ).length;

    const recentErrors = errors.filter(err => 
      !err.resolved && err.timestamp >= last10Minutes
    ).length;

    const details: string[] = [];

    let status: 'healthy' | 'degraded' | 'unhealthy' = 'healthy';

    if (criticalErrors > 0) {
      status = 'unhealthy';
      details.push(`${criticalErrors} critical error${criticalErrors > 1 ? 's' : ''} require immediate attention`);
    }

    if (highErrors > 3) {
      status = status === 'healthy' ? 'degraded' : status;
      details.push(`${highErrors} high severity errors detected`);
    }

    if (recentErrors > 5) {
      status = status === 'healthy' ? 'degraded' : status;
      details.push(`${recentErrors} errors in the last 10 minutes`);
    }

    if (status === 'healthy') {
      details.push('All telephony systems operating normally');
    }

    return {
      status,
      criticalErrors,
      highErrors,
      recentErrors,
      details
    };
  }
}

// Singleton instance for telephony error handling
export const telephonyErrorHandler = new TelephonyErrorHandler();