import { Controller, Get, Param, Query } from '@nestjs/common';
import { ApiOperation, ApiQuery, ApiResponse, ApiTags } from '@nestjs/swagger';
import { VehiclesService } from '../services/vehicles.service';
import { FilterVehicleDto } from '../dto/filter-vehicle.dto';

@ApiTags('Stores')
@Controller('api')
export class StoresController {
  constructor(private readonly vehiclesService: VehiclesService) {}

  @Get('stores')
  @ApiOperation({
    summary: 'Get overview of all 6 stores',
    description: 'Returns list of all stores with new/used vehicle counts and API links.',
  })
  @ApiResponse({ status: 200, description: 'Summary of all stores.' })
  public async getStoresOverview() {
    return this.vehiclesService.getStoresOverview();
  }

  // 1. Store 01 - Cheltenham Kia
  @Get(['stores/cheltenham-kia', 'stores/store01', 'store01'])
  @ApiOperation({
    summary: 'Store 01 - Cheltenham Kia vehicles',
    description: 'Get vehicles for Cheltenham Kia with optional ?type=new or ?type=used filter.',
  })
  @ApiQuery({ name: 'type', required: false, enum: ['new', 'used'] })
  public async getStore01(@Query() filterDto: FilterVehicleDto) {
    return this.vehiclesService.getVehiclesByStore('store01', filterDto);
  }

  // 2. Store 20 - Cranbourne Hyundai
  @Get(['stores/cranbourne-hyundai', 'stores/store20', 'store20'])
  @ApiOperation({
    summary: 'Store 20 - Cranbourne Hyundai vehicles',
    description: 'Get vehicles for Cranbourne Hyundai with optional ?type=new or ?type=used filter.',
  })
  @ApiQuery({ name: 'type', required: false, enum: ['new', 'used'] })
  public async getStore20(@Query() filterDto: FilterVehicleDto) {
    return this.vehiclesService.getVehiclesByStore('store20', filterDto);
  }

  // 3. Store 40 - South Morang Hyundai
  @Get(['stores/south-morang-hyundai', 'stores/store40', 'store40'])
  @ApiOperation({
    summary: 'Store 40 - South Morang Hyundai vehicles',
    description: 'Get vehicles for South Morang Hyundai with optional ?type=new or ?type=used filter.',
  })
  @ApiQuery({ name: 'type', required: false, enum: ['new', 'used'] })
  public async getStore40(@Query() filterDto: FilterVehicleDto) {
    return this.vehiclesService.getVehiclesByStore('store40', filterDto);
  }

  // 4. Store 50 - Dandenong Hyundai
  @Get(['stores/dandenong-hyundai', 'stores/store50', 'store50'])
  @ApiOperation({
    summary: 'Store 50 - Dandenong Hyundai vehicles',
    description: 'Get vehicles for Dandenong Hyundai with optional ?type=new or ?type=used filter.',
  })
  @ApiQuery({ name: 'type', required: false, enum: ['new', 'used'] })
  public async getStore50(@Query() filterDto: FilterVehicleDto) {
    return this.vehiclesService.getVehiclesByStore('store50', filterDto);
  }

  // 5. Store 70 - South Morang Kia
  @Get(['stores/south-morang-kia', 'stores/store70', 'store70'])
  @ApiOperation({
    summary: 'Store 70 - South Morang Kia vehicles',
    description: 'Get vehicles for South Morang Kia with optional ?type=new or ?type=used filter.',
  })
  @ApiQuery({ name: 'type', required: false, enum: ['new', 'used'] })
  public async getStore70(@Query() filterDto: FilterVehicleDto) {
    return this.vehiclesService.getVehiclesByStore('store70', filterDto);
  }

  // 6. Store 90 - Berwick Hyundai
  @Get(['stores/berwick-hyundai', 'stores/store90', 'store90'])
  @ApiOperation({
    summary: 'Store 90 - Berwick Hyundai vehicles',
    description: 'Get vehicles for Berwick Hyundai with optional ?type=new or ?type=used filter.',
  })
  @ApiQuery({ name: 'type', required: false, enum: ['new', 'used'] })
  public async getStore90(@Query() filterDto: FilterVehicleDto) {
    return this.vehiclesService.getVehiclesByStore('store90', filterDto);
  }

  // Dynamic Store Endpoint
  @Get('stores/:identifier')
  @ApiOperation({
    summary: 'Get vehicles by store identifier / slug',
    description:
      'Fetch vehicles using store identifier (e.g. store01, cheltenham-kia, 20, etc.) with optional ?type=new/used filter.',
  })
  @ApiQuery({ name: 'type', required: false, enum: ['new', 'used'] })
  public async getStoreByIdentifier(
    @Param('identifier') identifier: string,
    @Query() filterDto: FilterVehicleDto,
  ) {
    return this.vehiclesService.getVehiclesByStore(identifier, filterDto);
  }
}
