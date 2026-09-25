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
    console.log('🎉 CSV Import to MongoDB Completed!');
    console.log('========================================');
    console.log(`⏱️ Duration: ${(result.durationMs / 1000).toFixed(2)}s`);
    console.log(`📁 Files processed: ${result.files.length}`);
    console.log(`🚗 Total vehicles processed: ${result.totalProcessed}`);
    console.log(`💾 Total vehicles upserted in MongoDB: ${result.totalUpserted}`);
    console.log('----------------------------------------');
    console.log('File details:');
    result.files.forEach((f) => {
      console.log(`  - [${f.storeId}] (${f.type.toUpperCase()}) ${f.file}: ${f.count} vehicles`);
    });
    console.log('========================================\n');
  } catch (error) {
    console.error('❌ Error during seeding:', error);
    process.exit(1);
  } finally {
    await app.close();
    process.exit(0);
  }
}

bootstrap();
