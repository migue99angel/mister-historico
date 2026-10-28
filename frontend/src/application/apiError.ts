export type ApiErrorKind = 'problem' | 'transport' | 'unexpected-response';

export interface ApiErrorFields {
  status?: number;
  code?: string | undefined;
  title?: string | undefined;
  detail?: string | undefined;
  instance?: string | undefined;
}

/**
 * Error every GameApi adapter rejects with: part of the port's contract, so use-case hooks
 * and screens can branch on `instanceof ApiError`, `status` (e.g. 409) and `code`.
 */
export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | undefined;
  readonly code: string | undefined;
  readonly title: string | undefined;
  readonly detail: string | undefined;
  readonly instance: string | undefined;

  constructor(kind: ApiErrorKind, message: string, fields: ApiErrorFields = {}) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = fields.status;
    this.code = fields.code;
    this.title = fields.title;
    this.detail = fields.detail;
    this.instance = fields.instance;
  }
}
