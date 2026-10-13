import {
  Controller,
  Get,
  Post,
  Param,
  Query,
  HttpCode,
  HttpStatus,
  BadRequestException,
} from '@nestjs/common';
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

  @Get(['stores-by-stock', 'search-stores'])
  @ApiOperation({
    summary: 'Search stores carrying vehicle by stock number (query param)',
    description:
      'Search across all stores for a stock number and return all store names where it exists.',
  })
  @ApiQuery({
    name: 'stockNumber',
    required: true,
    description: 'Vehicle stock number, e.g. P251203',
  })
  @ApiResponse({
    status: 200,
    description: 'Returns store names where the vehicle exists.',
  })
  public async findStoresByStockQuery(
    @Query('stockNumber') stockNumber?: string,
  ) {
    if (!stockNumber || !stockNumber.trim()) {
      throw new BadRequestException('Query parameter "stockNumber" is required');
    }
    return this.vehiclesService.findStoresByStockNumber(stockNumber);
  }

  @Get([
    'stores-by-stock/:stockNumber',
    'search-stores/:stockNumber',
    'stock/:stockNumber/stores',
  ])
  @ApiOperation({
    summary: 'Search stores carrying vehicle by stock number (path param)',
    description:
      'Search across all stores for a stock number and return all store names where it exists.',
  })
  @ApiResponse({
    status: 200,
    description: 'Returns store names where the vehicle exists.',
  })
  public async findStoresByStockParam(
    @Param('stockNumber') stockNumber: string,
  ) {
    return this.vehiclesService.findStoresByStockNumber(stockNumber);
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
    description:
      'Parses all CSV files in the CSVs directory and upserts them into MongoDB.',
  })
  @ApiResponse({ status: 200, description: 'Sync completed successfully.' })
  public async syncCsvData() {
    return this.csvImporterService.syncAllCsvs();
  }
}
