import { NestFactory } from '@nestjs/core';
import { AppModule } from '../app.module';
import { CsvImporterService } from '../vehicles/services/csv-importer.service';

async function bootstrap() {
  console.log('🚀 Starting Booran Vehicles CSV Importer / Seeder...');
  const app = await NestFactory.createApplicationContext(AppModule);

  try {
    const csvImporter = app.get(CsvImporterService);
    const result = await csvImporter.syncAllCsvs();

    console.log('\n========================================');
    console.log('📋 BOORAN CSV SYNC & VERIFICATION REPORT');
    console.log('========================================\n');

    // 1. Any store numbers missing from STORES_MAP (blocking)
    console.log('1️⃣ STORE NUMBERS MISSING FROM STORES_MAP (BLOCKING):');
    if (result.missingStores.length === 0) {
      console.log('  None. All store numbers in CSV filenames are configured in STORES_MAP.\n');
    } else {
      console.log(
        `  ⚠️ Found ${result.missingStores.length} store number(s) missing from STORES_MAP (nothing from these stores was imported):`,
      );
      result.missingStores.forEach((ms) => {
        console.log(
          `    • Store "${ms.storeNumber}": ${ms.fileCount} file(s) blocked (e.g. "${ms.exampleFile}")`,
        );
      });
      console.log('  -> Action: Add entries to src/config/stores.config.ts to import these stores.\n');
    }

    // 2. Files skipped for other reasons
    console.log('2️⃣ FILES SKIPPED FOR OTHER REASONS (MALFORMED FILENAME / BAD TYPE TOKEN):');
    if (result.skippedFiles.length === 0) {
      console.log('  None (0 files skipped for formatting/token issues).\n');
    } else {
      result.skippedFiles.forEach((sf) => {
        console.log(`    • ${sf.file}: ${sf.reason}`);
      });
      console.log('');
    }

    // 3. Total files processed / records upserted
    console.log('3️⃣ TOTAL FILES PROCESSED / RECORDS UPSERTED:');
    console.log(`  • CSV Files Processed          : ${result.files.length}`);
    console.log(`  • Total Vehicle Records Read   : ${result.totalProcessed}`);
    console.log(`  • Total Vehicles Upserted (DB) : ${result.totalUpserted}`);
    console.log(`  • Execution Duration           : ${(result.durationMs / 1000).toFixed(2)}s\n`);

    // 4. Distinct brand values parsed
    console.log('4️⃣ DISTINCT BRAND VALUES PARSED (SANITY CHECK):');
    console.log(`  • Total Distinct Brands: ${result.distinctBrands.length}`);
    console.log(`  • Brands (${result.distinctBrands.length}):\n    ${result.distinctBrands.join(', ')}\n`);
    console.log('========================================\n');
  } catch (error) {
    console.error('❌ Error during seeding:', error);
    process.exit(1);
  } finally {
    await app.close();
    process.exit(0);
  }
}

void bootstrap();
