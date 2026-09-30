import { Injectable, Logger } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import * as fs from 'fs';
import * as path from 'path';
import { Transform } from 'stream';
// eslint-disable-next-line @typescript-eslint/no-require-imports
const csvParser = require('csv-parser');
import { Vehicle, VehicleDocument } from '../schemas/vehicle.schema';

/**
 * Stream transformer that sanitizes unescaped quotation marks within CSV fields
 * (e.g. 20" PACK AUTO UTE) before passing to csv-parser.
 */
class CsvSanitizerTransform extends Transform {
  private buffer = '';

  constructor() {
    super({ encoding: 'utf-8' });
  }

  _transform(chunk: any, _encoding: BufferEncoding, callback: () => void) {
    this.buffer += chunk.toString();
    const lines = this.buffer.split(/\r?\n/);
    this.buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.trim()) continue;
      const fixedLine = line.replace(/(?<!^|,)"(?!,|$)/g, '""');
      this.push(fixedLine + '\n');
    }
    callback();
  }

  _flush(callback: () => void) {
    if (this.buffer && this.buffer.trim()) {
      const fixedLine = this.buffer.replace(/(?<!^|,)"(?!,|$)/g, '""');
      this.push(fixedLine + '\n');
    }
    callback();
  }
}
import {
  STORES_MAP,
  StoreMeta,
  findStoreByIdentifier,
} from '../../config/stores.config';

export interface SyncFileResult {
  file: string;
  storeId: string;
  type: 'new' | 'used';
  brand?: string;
  count: number;
}

export interface MissingStoreInfo {
  storeNumber: string;
  exampleFile: string;
  fileCount: number;
}

export interface SkippedFileInfo {
  file: string;
  reason: string;
}

export interface SyncSummary {
  success: boolean;
  totalProcessed: number;
  totalUpserted: number;
  storesCount: number;
  files: SyncFileResult[];
  durationMs: number;
  missingStores: MissingStoreInfo[];
  skippedFiles: SkippedFileInfo[];
  distinctBrands: string[];
}

export type FilenameResolutionResult =
  | {
      status: 'valid';
      store: StoreMeta;
      storeNumber: string;
      type: 'new' | 'used';
      brand: string;
    }
  | {
      status: 'missing_store';
      storeNumber: string;
      reason: string;
    }
  | {
      status: 'invalid';
      reason: string;
    };

@Injectable()
export class CsvImporterService {
  private readonly logger = new Logger(CsvImporterService.name);

  constructor(
    @InjectModel(Vehicle.name)
    private readonly vehicleModel: Model<VehicleDocument>,
  ) {}

  /**
   * Parse 2-digit or 4-digit year into full number and original string
   */
  private parseYear(val?: any): {
    year: number | null;
    originalYear: string | null;
  } {
    if (val === undefined || val === null)
      return { year: null, originalYear: null };
    const str = String(val).trim();
    if (!str) return { year: null, originalYear: null };

    const num = parseInt(str, 10);
    if (isNaN(num)) return { year: null, originalYear: str };

    if (num < 100) {
      const fullYear = num > 50 ? 1900 + num : 2000 + num;
      return { year: fullYear, originalYear: str };
    }
    return { year: num, originalYear: str };
  }

  /**
   * Safely parse float/numeric values like list price and odometer
   */
  private parseNumber(val?: any): number | null {
    if (val === undefined || val === null) return null;
    const str = String(val).replace(/[$,]/g, '').trim();
    if (!str) return null;
    const num = parseFloat(str);
    return isNaN(num) ? null : num;
  }

  /**
   * Safely parse integer values like age
   */
  private parseInt(val?: any): number | null {
    if (val === undefined || val === null) return null;
    const str = String(val).replace(/[$,]/g, '').trim();
    if (!str) return null;
    const num = parseInt(str, 10);
    return isNaN(num) ? null : num;
  }

  /**
   * Resolve Store metadata, vehicle type ('new' | 'used'), and brand from CSV filename.
   * Supports both:
   *  - Modern downloader format: '{store}_{site}_{make}_{type}.csv' (e.g. '01_BooranCheltenham_AUDI_Used.csv')
   *  - Legacy format: 'Store{store}_{site}_{brand}_{type}.csv' (e.g. 'Store01_Cheltenham_Kia_new.csv')
   */
  public resolveStoreFromFilename(filename: string): FilenameResolutionResult {
    if (!filename.toLowerCase().endsWith('.csv')) {
      return {
        status: 'invalid',
        reason: 'File does not have a .csv extension',
      };
    }

    const baseName = filename.slice(0, -4);
    const parts = baseName.split('_');

    if (parts.length < 2) {
      return {
        status: 'invalid',
        reason:
          'Malformed filename: missing underscore delimiter to separate store and type tokens',
      };
    }

    // First underscore-segment is the store segment (e.g. "01", "Store01", "20", "51")
    const rawStoreSegment = parts[0].trim();
    if (!rawStoreSegment) {
      return {
        status: 'invalid',
        reason: 'Malformed filename: missing store number prefix',
      };
    }
    const cleanStoreNumber = rawStoreSegment.replace(/^store/i, '').trim();

    // Last underscore-segment is vehicle condition ('new' | 'used')
    const rawType = parts[parts.length - 1].trim().toLowerCase();
    if (rawType !== 'new' && rawType !== 'used') {
      return {
        status: 'invalid',
        reason: `Invalid vehicle type token "${parts[parts.length - 1]}" (expected "New" or "Used")`,
      };
    }
    const type: 'new' | 'used' = rawType;

    // Cross-check store in STORES_MAP / STORES_LIST
    const store =
      findStoreByIdentifier(rawStoreSegment) ||
      findStoreByIdentifier(cleanStoreNumber) ||
      STORES_MAP[`store${cleanStoreNumber}`] ||
      STORES_MAP[cleanStoreNumber];

    if (!store) {
      return {
        status: 'missing_store',
        storeNumber: cleanStoreNumber || rawStoreSegment,
        reason: `Store number "${cleanStoreNumber || rawStoreSegment}" is missing from STORES_MAP`,
      };
    }

    // Parse brand/make: segment immediately preceding type token if >= 3 parts, else fallback to store brand
    const brand =
      parts.length >= 3 ? parts[parts.length - 2].trim() : store.brand;

    return {
      status: 'valid',
      store,
      storeNumber: store.storeNumber,
      type,
      brand: brand || store.brand,
    };
  }

  /**
   * Read and parse a single CSV file into normalized vehicle records
   */
  public async parseCsvFile(filePath: string): Promise<{
    meta: {
      store: StoreMeta;
      type: 'new' | 'used';
      brand: string;
      filename: string;
    };
    records: Partial<Vehicle>[];
  }> {
    const filename = path.basename(filePath);
    const resolved = this.resolveStoreFromFilename(filename);

    if (resolved.status !== 'valid') {
      const reason =
        resolved.status === 'missing_store'
          ? `Store number "${resolved.storeNumber}" is missing from STORES_MAP`
          : resolved.reason;
      throw new Error(`Unable to parse ${filename}: ${reason}`);
    }

    const { store, type, brand } = resolved;
    const records: Partial<Vehicle>[] = [];

    return new Promise((resolve, reject) => {
      fs.createReadStream(filePath)
        .pipe(new CsvSanitizerTransform())
        .pipe(csvParser())
        .on('data', (row: Record<string, string>) => {
          const rawStock = row['stock#'] || row['stock no'] || '';
          const stockNumber = String(rawStock).trim();

          // Skip empty rows
          if (!stockNumber) return;

          const yearInfo = this.parseYear(row['year']);
          const listPrice = this.parseNumber(row['list price']);
          const odometer = this.parseNumber(row['odometer']);
          const age = this.parseInt(row['age']);

          const vehicle: Partial<Vehicle> = {
            storeId: store.storeId,
            storeNumber: store.storeNumber,
            storeName: store.name,
            storeSlug: store.slug,
            brand: brand || store.brand,
            type,
            stockNumber,
            carline: (row['carline'] || '').trim(),
            description: (row['description'] || '').trim(),
            colour: (row['colour'] || '').trim(),
            location: (row['loc'] || '').trim(),
            destLocation: (row['dest loc'] || '').trim(),
            listPrice,
            age,
            status: (row['status'] || '').trim(),
            openRoPo: (row['open ro/po'] || '').trim(),
            fa:
              row['fa'] !== undefined ? String(row['fa']).trim() || null : null,
            deal:
              row['deal'] !== undefined
                ? String(row['deal']).trim() || null
                : null,
            year: yearInfo.year,
            originalYear: yearInfo.originalYear,
            regNo: row['reg no'] ? String(row['reg no']).trim() : null,
            odometer,
            sourceFile: filename,
          };

          records.push(vehicle);
        })
        .on('end', () => {
          resolve({ meta: { store, type, brand, filename }, records });
        })
        .on('error', (err: Error) => {
          reject(err);
        });
    });
  }

  /**
   * Sync all CSV files in the CSV directory into MongoDB with pre-sync cross-check verification
   */
  public async syncAllCsvs(csvDirectoryPath?: string): Promise<SyncSummary> {
    const startTime = Date.now();
    const defaultDir = fs.existsSync(
      path.resolve(process.cwd(), 'erapower_downloads'),
    )
      ? path.resolve(process.cwd(), 'erapower_downloads')
      : path.resolve(process.cwd(), 'CSVs');
    const csvDir = csvDirectoryPath || process.env.CSV_DIR || defaultDir;

    if (!fs.existsSync(csvDir)) {
      throw new Error(`CSV directory does not exist: ${csvDir}`);
    }

    const allCsvFiles = fs
      .readdirSync(csvDir)
      .filter((file) => file.toLowerCase().endsWith('.csv'));

    this.logger.log(`Found ${allCsvFiles.length} CSV files in ${csvDir}`);

    // Pre-sync verification & cross-check against STORES_MAP
    const missingStoresMap = new Map<string, MissingStoreInfo>();
    const skippedFiles: SkippedFileInfo[] = [];
    const validFilesToProcess: {
      file: string;
      resolved: Extract<FilenameResolutionResult, { status: 'valid' }>;
    }[] = [];

    for (const file of allCsvFiles) {
      const resolution = this.resolveStoreFromFilename(file);
      if (resolution.status === 'missing_store') {
        const existing = missingStoresMap.get(resolution.storeNumber);
        if (existing) {
          existing.fileCount++;
        } else {
          missingStoresMap.set(resolution.storeNumber, {
            storeNumber: resolution.storeNumber,
            exampleFile: file,
            fileCount: 1,
          });
        }
      } else if (resolution.status === 'invalid') {
        skippedFiles.push({ file, reason: resolution.reason });
      } else {
        validFilesToProcess.push({ file, resolved: resolution });
      }
    }

    // Log warnings for any store numbers missing from STORES_MAP
    if (missingStoresMap.size > 0) {
      this.logger.warn(
        `⚠️ Found ${missingStoresMap.size} distinct store number(s) present in CSV filenames but MISSING from STORES_MAP. These files will be SKIPPED without failing the sync:`,
      );
      for (const missing of missingStoresMap.values()) {
        this.logger.warn(
          `  - Store "${missing.storeNumber}": ${missing.fileCount} file(s) skipped (e.g. "${missing.exampleFile}")`,
        );
      }
    }

    // Log warnings for files skipped for other reasons
    if (skippedFiles.length > 0) {
      this.logger.warn(
        `⚠️ Found ${skippedFiles.length} file(s) skipped for other reasons:`,
      );
      for (const skipped of skippedFiles) {
        this.logger.warn(`  - "${skipped.file}": ${skipped.reason}`);
      }
    }

    // Automatically purge redundant legacy DMS records from older imports
    const deletedLegacy = await this.vehicleModel.deleteMany({
      sourceFile: { $regex: /^Store\d+/i },
    });
    if (deletedLegacy.deletedCount > 0) {
      this.logger.log(
        `Cleaned up ${deletedLegacy.deletedCount} redundant legacy records from earlier imports.`,
      );
    }

    const fileResults: SyncFileResult[] = [];
    const distinctBrandsSet = new Set<string>();
    let totalProcessed = 0;
    let totalUpserted = 0;

    for (const { file, resolved } of validFilesToProcess) {
      const filePath = path.join(csvDir, file);
      try {
        const { meta, records } = await this.parseCsvFile(filePath);

        if (meta.brand) {
          distinctBrandsSet.add(meta.brand);
        }

        if (records.length === 0) {
          this.logger.warn(`No inventory records found in ${file}`);
          fileResults.push({
            file,
            storeId: meta.store.storeId,
            type: meta.type,
            brand: meta.brand,
            count: 0,
          });
          continue;
        }

        // Deduplicate in-memory by stockNumber within the file
        const uniqueMap = new Map<string, Partial<Vehicle>>();
        for (const record of records) {
          if (record.stockNumber) {
            uniqueMap.set(record.stockNumber, record);
          }
        }
        const uniqueRecords = Array.from(uniqueMap.values());

        // Bulk upsert to MongoDB
        const bulkOps = uniqueRecords.map((record) => ({
          updateOne: {
            filter: {
              storeId: record.storeId,
              stockNumber: record.stockNumber,
            },
            update: { $set: record },
            upsert: true,
          },
        }));

        const result = await this.vehicleModel.bulkWrite(bulkOps, {
          ordered: false,
        });

        const upsertedOrModified =
          (result.upsertedCount || 0) +
          (result.modifiedCount || 0) +
          (result.matchedCount || 0);

        totalProcessed += uniqueRecords.length;
        totalUpserted += upsertedOrModified;

        fileResults.push({
          file,
          storeId: meta.store.storeId,
          type: meta.type,
          brand: meta.brand,
          count: uniqueRecords.length,
        });

        this.logger.log(
          `Processed ${file}: ${uniqueRecords.length} vehicles for ${meta.store.name} (${meta.type}, brand: ${meta.brand})`,
        );
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : String(err);
        const errStack = err instanceof Error ? err.stack : undefined;
        this.logger.error(`Error processing file ${file}: ${errMsg}`, errStack);
      }
    }

    const durationMs = Date.now() - startTime;

    return {
      success: true,
      totalProcessed,
      totalUpserted,
      storesCount: Object.keys(STORES_MAP).length,
      files: fileResults,
      durationMs,
      missingStores: Array.from(missingStoresMap.values()).sort((a, b) =>
        a.storeNumber.localeCompare(b.storeNumber),
      ),
      skippedFiles,
      distinctBrands: Array.from(distinctBrandsSet).sort(),
    };
  }
}
