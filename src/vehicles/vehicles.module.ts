import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import { Vehicle, VehicleSchema } from './schemas/vehicle.schema';
import { VehiclesService } from './services/vehicles.service';
import { CsvImporterService } from './services/csv-importer.service';
import { StoresController } from './controllers/stores.controller';
import { VehiclesController } from './controllers/vehicles.controller';

@Module({
  imports: [
    MongooseModule.forFeature([{ name: Vehicle.name, schema: VehicleSchema }]),
  ],
  controllers: [StoresController, VehiclesController],
  providers: [VehiclesService, CsvImporterService],
  exports: [VehiclesService, CsvImporterService],
})
export class VehiclesModule {}
