/**
 * D2D MCP Tools Module
 *
 * This module can be imported into your existing Cloud Run MCP server
 * to add D2D (Documents to DICOM) capabilities.
 *
 * Usage:
 *   import { d2dTools, handleD2dTool } from './d2d-tools.js';
 *
 *   // Add to your tool list
 *   const allTools = [...yourExistingTools, ...d2dTools];
 *
 *   // In your tool handler
 *   if (toolName.startsWith('d2d_')) {
 *     return await handleD2dTool(toolName, args);
 *   }
 */

import fetch from 'node-fetch';
import FormData from 'form-data';
import { readFile } from 'fs/promises';

/**
 * D2D Configuration
 * Set these via environment variables in Cloud Run
 */
const D2D_CONFIG = {
  apiUrl: process.env.D2D_API_URL || 'http://localhost:8000',
  apiKey: process.env.D2D_API_KEY || '',
  timeout: parseInt(process.env.D2D_TIMEOUT || '30000'),
};

/**
 * Helper function to make API calls to D2D
 */
async function d2dApiCall(endpoint, options = {}) {
  const url = `${D2D_CONFIG.apiUrl}${endpoint}`;
  const headers = {
    ...options.headers,
  };

  if (D2D_CONFIG.apiKey) {
    headers['X-API-Key'] = D2D_CONFIG.apiKey;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), D2D_CONFIG.timeout);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeout);

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`D2D API error: ${response.status} - ${error}`);
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }

    return await response.text();
  } catch (error) {
    clearTimeout(timeout);
    if (error.name === 'AbortError') {
      throw new Error('D2D API request timeout');
    }
    throw error;
  }
}

/**
 * D2D Tool Definitions
 * Export this array to add to your MCP server's tool list
 */
export const d2dTools = [
  {
    name: 'd2d_health_check',
    description: 'Check if D2D server is running and healthy',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'd2d_upload_file',
    description: 'Upload a document (PDF, JPG, PNG) to D2D for DICOM conversion',
    inputSchema: {
      type: 'object',
      properties: {
        file_path: {
          type: 'string',
          description: 'Path to the file to upload',
        },
        patient_name: {
          type: 'string',
          description: 'Patient name in DICOM format (LastName^FirstName)',
        },
        patient_id: {
          type: 'string',
          description: 'Patient ID or MRN',
        },
        patient_dob: {
          type: 'string',
          description: 'Patient date of birth (YYYYMMDD format, optional)',
        },
        patient_sex: {
          type: 'string',
          description: 'Patient sex (M, F, or O, optional)',
        },
        study_description: {
          type: 'string',
          description: 'Study description (optional)',
        },
        accession_number: {
          type: 'string',
          description: 'Accession number (optional)',
        },
      },
      required: ['file_path', 'patient_name', 'patient_id'],
    },
  },
  {
    name: 'd2d_list_destinations',
    description: 'List all configured DICOM destinations (PACS servers)',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'd2d_add_destination',
    description: 'Add a new DICOM destination (PACS server)',
    inputSchema: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'Friendly name for the destination',
        },
        ae_title: {
          type: 'string',
          description: 'PACS AE Title',
        },
        host: {
          type: 'string',
          description: 'PACS hostname or IP address',
        },
        port: {
          type: 'number',
          description: 'PACS DICOM port',
        },
        calling_ae_title: {
          type: 'string',
          description: 'Calling AE Title (source)',
        },
      },
      required: ['name', 'ae_title', 'host', 'port', 'calling_ae_title'],
    },
  },
  {
    name: 'd2d_verify_destination',
    description: 'Test connection to a DICOM destination (C-ECHO)',
    inputSchema: {
      type: 'object',
      properties: {
        ae_title: {
          type: 'string',
          description: 'PACS AE Title',
        },
        host: {
          type: 'string',
          description: 'PACS hostname or IP address',
        },
        port: {
          type: 'number',
          description: 'PACS DICOM port',
        },
        calling_ae_title: {
          type: 'string',
          description: 'Calling AE Title (source)',
        },
      },
      required: ['ae_title', 'host', 'port', 'calling_ae_title'],
    },
  },
  {
    name: 'd2d_send_to_pacs',
    description: 'Send a converted DICOM file to a PACS destination',
    inputSchema: {
      type: 'object',
      properties: {
        filename: {
          type: 'string',
          description: 'Name of the DICOM file in the archive',
        },
        destination: {
          type: 'string',
          description: 'Name of the destination (from list_destinations)',
        },
      },
      required: ['filename', 'destination'],
    },
  },
  {
    name: 'd2d_list_archives',
    description: 'List all archived DICOM files',
    inputSchema: {
      type: 'object',
      properties: {
        limit: {
          type: 'number',
          description: 'Maximum number of files to return (optional)',
        },
      },
    },
  },
  {
    name: 'd2d_convert_document',
    description: 'Convert an uploaded document to DICOM format',
    inputSchema: {
      type: 'object',
      properties: {
        filename: {
          type: 'string',
          description: 'Name of the uploaded file',
        },
        patient_name: {
          type: 'string',
          description: 'Patient name in DICOM format',
        },
        patient_id: {
          type: 'string',
          description: 'Patient ID or MRN',
        },
        patient_dob: {
          type: 'string',
          description: 'Patient DOB (YYYYMMDD, optional)',
        },
        patient_sex: {
          type: 'string',
          description: 'Patient sex (M/F/O, optional)',
        },
        study_description: {
          type: 'string',
          description: 'Study description (optional)',
        },
        modality: {
          type: 'string',
          description: 'DICOM modality code (default: DOC)',
        },
      },
      required: ['filename', 'patient_name', 'patient_id'],
    },
  },
];

/**
 * D2D Tool Handler
 * Export this function to handle D2D tool calls in your MCP server
 */
export async function handleD2dTool(toolName, args) {
  try {
    switch (toolName) {
      case 'd2d_health_check': {
        const result = await d2dApiCall('/api/health');
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case 'd2d_upload_file': {
        const formData = new FormData();

        // Check if file_path is a URL or local file
        let fileBuffer;
        let fileName;

        if (args.file_path.startsWith('http://') || args.file_path.startsWith('https://')) {
          // Download from URL
          const response = await fetch(args.file_path);
          fileBuffer = Buffer.from(await response.arrayBuffer());
          fileName = args.file_path.split('/').pop() || 'upload.pdf';
        } else {
          // Read local file
          fileBuffer = await readFile(args.file_path);
          fileName = args.file_path.split('/').pop();
        }

        formData.append('file', fileBuffer, fileName);
        formData.append('patient_name', args.patient_name);
        formData.append('patient_id', args.patient_id);

        if (args.patient_dob) formData.append('patient_dob', args.patient_dob);
        if (args.patient_sex) formData.append('patient_sex', args.patient_sex);
        if (args.study_description) formData.append('study_description', args.study_description);
        if (args.accession_number) formData.append('accession_number', args.accession_number);

        const result = await d2dApiCall('/api/upload', {
          method: 'POST',
          body: formData,
          headers: formData.getHeaders(),
        });

        return {
          content: [
            {
              type: 'text',
              text: `File uploaded and converted successfully:\n${JSON.stringify(result, null, 2)}`,
            },
          ],
        };
      }

      case 'd2d_list_destinations': {
        const result = await d2dApiCall('/api/destinations');
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case 'd2d_add_destination': {
        const result = await d2dApiCall('/api/destinations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(args),
        });

        return {
          content: [
            {
              type: 'text',
              text: `Destination added successfully:\n${JSON.stringify(result, null, 2)}`,
            },
          ],
        };
      }

      case 'd2d_verify_destination': {
        const result = await d2dApiCall('/api/destinations/verify', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(args),
        });

        return {
          content: [
            {
              type: 'text',
              text: `Connection test result:\n${JSON.stringify(result, null, 2)}`,
            },
          ],
        };
      }

      case 'd2d_send_to_pacs': {
        const result = await d2dApiCall('/api/send', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(args),
        });

        return {
          content: [
            {
              type: 'text',
              text: `DICOM file sent successfully:\n${JSON.stringify(result, null, 2)}`,
            },
          ],
        };
      }

      case 'd2d_list_archives': {
        const endpoint = args.limit ? `/api/archives?limit=${args.limit}` : '/api/archives';
        const result = await d2dApiCall(endpoint);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case 'd2d_convert_document': {
        const result = await d2dApiCall('/api/convert', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(args),
        });

        return {
          content: [
            {
              type: 'text',
              text: `Document converted to DICOM:\n${JSON.stringify(result, null, 2)}`,
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown D2D tool: ${toolName}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error executing ${toolName}: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
}

/**
 * Health check function for monitoring
 */
export async function checkD2dHealth() {
  try {
    const result = await d2dApiCall('/api/health');
    return { healthy: true, ...result };
  } catch (error) {
    return { healthy: false, error: error.message };
  }
}

export default {
  tools: d2dTools,
  handler: handleD2dTool,
  healthCheck: checkD2dHealth,
};
