export class ApiError extends Error {
  constructor(
    public status: number,
    public data: any
  ) {
    super(`API Error: ${status}`);
    this.name = 'ApiError';
  }

  getUserMessage(): string {
    // Network errors
    if (this.status === 0) {
      return 'Unable to connect. Please check your internet connection.';
    }

    // Rate limiting
    if (this.status === 429) {
      return 'Too many requests. Please wait a moment and try again.';
    }

    // Authentication
    if (this.status === 401) {
      return 'Your session has expired. Please log in again.';
    }

    if (this.status === 403) {
      return 'You do not have permission to perform this action.';
    }

    // Service unavailable — backend sent a specific reason (e.g. missing API key)
    if (this.status === 503 && this.data?.detail) {
      return this.data.detail;
    }

    // Server errors
    if (this.status >= 500) {
      return 'Our servers are having trouble. Please try again in a moment.';
    }

    // Client errors - try to extract message from data
    if (this.data?.message) {
      return this.data.message;
    }

    if (this.data?.errors && Array.isArray(this.data.errors) && this.data.errors.length > 0) {
      return this.data.errors[0].message || 'Something went wrong.';
    }

    return 'Something went wrong. Please try again.';
  }
}
