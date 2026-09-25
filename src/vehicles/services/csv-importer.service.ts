import { Injectable, Logger } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import * as fs from 'fs';
import * as path from 'path';
// eslint-disable-next-line @typescript-eslint/no-require-imports
const csvParser = require('csv-parser');
import { Vehicle, VehicleDocument } from '../schemas/vehicle.schema';
import { STORES_MAP, StoreMeta } from '../../config/stores.config';

export interface SyncFileResult {
  file: string;
  storeId: string;
  type: 'new' | 'used';
  count: number;
}

export interface SyncSummary {
  success: boolean;
  totalProcessed: number;
  totalUpserted: number;
  storesCount: number;
  files: SyncFileResult[];
  durationMs: number;
}

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
  private parseYear(val?: any): { year: number | null; originalYear: string | null } {
    if (val === undefined || val === null) return { year: null, originalYear: null };
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
   * Resolve Store metadata from filename
   * Example: 'Store01_Cheltenham_Kia_new.csv'
   */
  private resolveStoreFromFilename(filename: string): {
    store: StoreMeta;
    type: 'new' | 'used';
  } | null {
    const match = filename.match(/Store(\d+).*?_(new|used)\.csv$/i);
    if (!match) return null;

    const storeNumber = match[1];
    const type = match[2].toLowerCase() as 'new' | 'used';
    const storeKey = `store${storeNumber}`;
    const store = STORES_MAP[storeKey];

    if (!store) {
      this.logger.warn(`Unknown store identified for filename: ${filename}`);
      return null;
    }

    return { store, type };
  }

  /**
   * Read and parse a single CSV file into normalized vehicle records
   */
  public async parseCsvFile(filePath: string): Promise<{
    meta: { store: StoreMeta; type: 'new' | 'used'; filename: string };
    records: Partial<Vehicle>[];
  }> {
    const filename = path.basename(filePath);
    const resolved = this.resolveStoreFromFilename(filename);

    if (!resolved) {
      throw new Error(`Unable to resolve store and type from filename: ${filename}`);
    }

    const { store, type } = resolved;
    const records: Partial<Vehicle>[] = [];

    return new Promise((resolve, reject) => {
      fs.createReadStream(filePath)
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
            brand: store.brand,
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
            fa: row['fa'] !== undefined ? String(row['fa']).trim() || null : null,
            deal: row['deal'] !== undefined ? String(row['deal']).trim() || null : null,
            year: yearInfo.year,
            originalYear: yearInfo.originalYear,
            regNo: row['reg no'] ? String(row['reg no']).trim() : null,
            odometer,
            sourceFile: filename,
          };

          records.push(vehicle);
        })
        .on('end', () => {
          resolve({ meta: { store, type, filename }, records });
        })
        .on('error', (err) => {
          reject(err);
        });
    });
  }

  /**
   * Sync all CSV files in the CSV directory into MongoDB
   */
  public async syncAllCsvs(csvDirectoryPath?: string): Promise<SyncSummary> {
    const startTime = Date.now();
    const csvDir =
      csvDirectoryPath ||
      path.resolve(process.cwd(), 'CSVs');

    if (!fs.existsSync(csvDir)) {
      throw new Error(`CSV directory does not exist: ${csvDir}`);
    }

    const files = fs
      .readdirSync(csvDir)
      .filter((file) => file.toLowerCase().endsWith('.csv'));

    this.logger.log(`Found ${files.length} CSV files in ${csvDir}`);

    const fileResults: SyncFileResult[] = [];
    let totalProcessed = 0;
    let totalUpserted = 0;

    for (const file of files) {
      const filePath = path.join(csvDir, file);
      try {
        const { meta, records } = await this.parseCsvFile(filePath);

        if (records.length === 0) {
          this.logger.warn(`No records found in ${file}`);
          continue;
        }

        // Bulk upsert to MongoDB
        const bulkOps = records.map((record) => ({
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

        totalProcessed += records.length;
        totalUpserted += upsertedOrModified;

        fileResults.push({
          file,
          storeId: meta.store.storeId,
          type: meta.type,
          count: records.length,
        });

        this.logger.log(
          `Processed ${file}: ${records.length} vehicles for ${meta.store.name} (${meta.type})`,
        );
      } catch (err) {
        this.logger.error(`Error processing file ${file}: ${err.message}`, err.stack);
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
    };
  }
}
