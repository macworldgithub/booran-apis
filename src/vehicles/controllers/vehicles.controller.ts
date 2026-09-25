import { Controller, Get, Post, Param, Query, HttpCode, HttpStatus } from '@nestjs/common';
import { ApiOperation, ApiQuery, ApiResponse, ApiTags } from '@nestjs/swagger';
import { VehiclesService } from '../services/vehicles.service';
import { CsvImporterService } from '../services/csv-importer.service';
import { FilterVehicleDto } from '../dto/filter-vehicle.dto';

@ApiTags('Vehicles')
@Controller('api/vehicles')
export class VehiclesController {
  constructor(
    private readonly vehiclesService: VehiclesService,
    private readonly csvImporterService: CsvImporterService,
  ) {}

  @Get()
  @ApiOperation({
    summary: 'Search & filter vehicles across all stores',
    description:
      'Search across all stores or filter by store, type (new/used), carline, brand, etc.',
  })
  @ApiQuery({ name: 'type', required: false, enum: ['new', 'used'] })
  @ApiQuery({ name: 'store', required: false })
  @ApiQuery({ name: 'brand', required: false })
  @ApiQuery({ name: 'carline', required: false })
  @ApiQuery({ name: 'search', required: false })
  public async getAllVehicles(@Query() filterDto: FilterVehicleDto) {
    return this.vehiclesService.getAllVehicles(filterDto);
  }

  @Get(':stockNumber')
  @ApiOperation({
    summary: 'Get vehicle by stock number',
    description: 'Fetch vehicle details using unique stock number.',
  })
  public async getVehicleByStock(@Param('stockNumber') stockNumber: string) {
    return this.vehiclesService.getVehicleByStock(stockNumber);
  }

  @Post('sync')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({
    summary: 'Sync CSV files to MongoDB',
    description: 'Parses all CSV files in the CSVs directory and upserts them into MongoDB.',
  })
  @ApiResponse({ status: 200, description: 'Sync completed successfully.' })
  public async syncCsvData() {
    return this.csvImporterService.syncAllCsvs();
  }
}
