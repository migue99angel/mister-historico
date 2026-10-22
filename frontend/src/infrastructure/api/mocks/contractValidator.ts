import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { Ajv2020 } from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import { parse } from 'yaml';

/**
 * Validates API replies against `contracts/openapi.yaml`. Test support only: it reads the
 * contract from disk, so it must never be imported by application code.
 */

type Json = Record<string, unknown>;

const CONTRACT_PATH = resolve(import.meta.dirname, '../../../../../contracts/openapi.yaml');
const SCHEMA_ID = 'urn:mister-historico:openapi';

/** The parsed OpenAPI document. */
export const openApiDocument = parse(readFileSync(CONTRACT_PATH).toString()) as Json;

// OpenAPI 3.1 schemas are JSON Schema 2020-12. `strict: false` tolerates OpenAPI-only keywords.
const ajv = new Ajv2020({ strict: false, allErrors: true });
// ajv-formats ships CommonJS: under bundler resolution its default export is the module object.
(addFormats as unknown as { default: (instance: Ajv2020) => Ajv2020 }).default(ajv);
ajv.addSchema({ ...openApiDocument, $id: SCHEMA_ID });

function pointer(ref: string): unknown {
  return ref
    .replace(/^#\//, '')
    .split('/')
    .reduce<unknown>((node, key) => (node as Json | undefined)?.[key], openApiDocument);
}

function deref<T extends Json>(node: T | { $ref: string }): T {
  return '$ref' in node ? (pointer(node.$ref as string) as T) : node;
}

/**
 * Returns the list of contract violations of a reply (empty when it conforms).
 *
 * @param method HTTP method.
 * @param template Path template exactly as written in the contract, e.g. `/runs/{runId}`.
 * @param status HTTP status of the reply.
 * @param body Parsed JSON body, or `undefined` when empty.
 * @param contentType Value of the `Content-Type` header.
 */
export function validateResponse(
  method: string,
  template: string,
  status: number,
  body: unknown,
  contentType: string,
): string[] {
  const paths = openApiDocument.paths as Record<string, Record<string, Json>>;
  const operation = paths[template]?.[method.toLowerCase()];
  if (!operation) return [`${method} ${template} is not declared in the contract`];

  const declared = (operation.responses as Record<string, Json>)[String(status)];
  if (!declared) return [`status ${String(status)} is not declared for ${method} ${template}`];

  const content = deref(declared).content as Record<string, { schema?: Json }> | undefined;
  if (!content) {
    return body === undefined ? [] : [`status ${String(status)} must have an empty body`];
  }

  const mediaType = Object.keys(content).find((type) => contentType.startsWith(type));
  const schema = mediaType ? content[mediaType]?.schema : undefined;
  if (!mediaType || !schema) {
    return [`content type "${contentType}" is not declared for status ${String(status)}`];
  }

  const ref = (schema as { $ref?: string }).$ref;
  const validate = ajv.compile(ref ? { $ref: `${SCHEMA_ID}${ref}` } : schema);
  if (validate(body)) return [];
  return (validate.errors ?? []).map((error) => `${error.instancePath} ${error.message ?? ''}`);
}
