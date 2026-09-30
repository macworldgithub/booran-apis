import { Controller, Get, Param, Query, applyDecorators } from '@nestjs/common';
import { ApiOperation, ApiQuery, ApiResponse, ApiTags } from '@nestjs/swagger';
import { VehiclesService } from '../services/vehicles.service';
import { FilterVehicleDto } from '../dto/filter-vehicle.dto';

function ApiStoreFilterQueries() {
  return applyDecorators(
    ApiQuery({
      name: 'type',
      required: false,
      enum: ['new', 'used'],
      description: 'Filter by vehicle category (new or used)',
    }),
    ApiQuery({
      name: 'brand',
      required: false,
      description:
        'Filter by vehicle make/brand (e.g. TOYOTA, BMW, HYUNDAI, CHERY, FORD, KIA, MAZDA, etc.)',
    }),
    ApiQuery({
      name: 'carline',
      required: false,
      description:
        'Filter by model line (e.g. CARNIVAL, TUCSON, SELTOS, RANGER)',
    }),
    ApiQuery({
      name: 'status',
      required: false,
      description:
        'Filter by stock status (e.g. IN-STOCK, LOANER, DEMO, WHOLESALE)',
    }),
    ApiQuery({
      name: 'search',
      required: false,
      description:
        'Keyword search across description, stockNumber, colour, regNo',
    }),
    ApiQuery({
      name: 'limit',
      required: false,
      type: Number,
      description: 'Records per page (omit to fetch all matching vehicles)',
    }),
    ApiQuery({
      name: 'page',
      required: false,
      type: Number,
      description: '1-indexed page offset when using limit',
    }),
    ApiQuery({
      name: 'sort',
      required: false,
      enum: ['listPrice', 'age', 'year'],
      description: 'Sort field',
    }),
    ApiQuery({
      name: 'order',
      required: false,
      enum: ['asc', 'desc'],
      description: 'Sort direction (asc or desc)',
    }),
  );
}

@ApiTags('Stores')
@Controller('api')
export class StoresController {
  constructor(private readonly vehiclesService: VehiclesService) {}

  @Get('stores')
  @ApiOperation({
    summary: 'Get overview of all 8 stores with in-stock makes breakdown',
    description:
      'Returns list of all 8 stores with live new/used vehicle counts, distinct makes count, and exact makes lists (new, used, and all) available at each rooftop.',
  })
  @ApiResponse({ status: 200, description: 'Summary of all 8 stores.' })
  public async getStoresOverview() {
    return this.vehiclesService.getStoresOverview();
  }

  // 1. Store 01 - Cheltenham Kia
  @Get(['stores/cheltenham-kia', 'stores/store01', 'store01'])
  @ApiOperation({
    summary: 'Store 01 - Cheltenham Kia vehicles (23 distinct makes in stock)',
    description:
      'Get inventory for Cheltenham Kia with multi-make support (Kia, Chery, Skoda, Isuzu, Audi, BMW, Toyota, Ford, etc.) and filtering by ?brand=, ?type=, ?carline=, ?search=.',
  })
  @ApiStoreFilterQueries()
  public async getStore01(@Query() filterDto: FilterVehicleDto) {
    return this.vehiclesService.getVehiclesByStore('store01', filterDto);
  }

  // 2. Store 20 - Cranbourne Hyundai
  @Get(['stores/cranbourne-hyundai', 'stores/store20', 'store20'])
  @ApiOperation({
    summary:
      'Store 20 - Cranbourne Hyundai vehicles (17 distinct makes in stock)',
    description:
      'Get inventory for Cranbourne Hyundai with multi-make support (Hyundai, Chery, Ford, Toyota, Nissan, Holden, Mazda, etc.) and filtering by ?brand=, ?type=, ?carline=, ?search=.',
  })
  @ApiStoreFilterQueries()
  public async getStore20(@Query() filterDto: FilterVehicleDto) {
    return this.vehiclesService.getVehiclesByStore('store20', filterDto);
  }

  // 3. Store 40 - South Morang Hyundai
  @Get(['stores/south-morang-hyundai', 'stores/store40', 'store40'])
  @ApiOperation({
    summary:
      'Store 40 - South Morang Hyundai vehicles (18 distinct makes in stock)',
    description:
      'Get inventory for South Morang Hyundai with multi-make support (Hyundai in new; BMW, Ford, Holden, Honda, Mazda, MG, Mitsubishi, Nissan, Subaru, Suzuki, Toyota, VW in used) and filtering by ?brand=, ?type=, ?carline=, ?search=.',
  })
  @ApiStoreFilterQueries()
  public async getStore40(@Query() filterDto: FilterVehicleDto) {
    return this.vehiclesService.getVehiclesByStore('store40', filterDto);
  }

  // 4. Store 50 - Dandenong Mitsubishi & Hyundai
  @Get(['stores/dandenong-hyundai', 'stores/store50', 'store50'])
  @ApiOperation({
    summary:
      'Store 50 - Dandenong Mitsubishi & Hyundai vehicles (17 distinct makes in stock)',
    description:
      'Get inventory for Dandenong Mitsubishi & Hyundai with multi-make support (Kia, Chery, Geely, Great Wall, Omoda/Jaecoo, Hyundai, MG, GAC, Mitsubishi, Ford, etc.) and filtering by ?brand=, ?type=, ?carline=, ?search=.',
  })
  @ApiStoreFilterQueries()
  public async getStore50(@Query() filterDto: FilterVehicleDto) {
    return this.vehiclesService.getVehiclesByStore('store50', filterDto);
  }

  // 5. Store 51 - Cranbourne MG / Mitsubishi / Kia
  @Get(['stores/cranbourne-mg-mits-kia', 'stores/store51', 'store51'])
  @ApiOperation({
    summary:
      'Store 51 - Cranbourne MG / Mitsubishi / Kia vehicles (39 distinct makes in stock)',
    description:
      'Get inventory for Cranbourne MG / Mitsubishi / Kia with multi-make support (Kia, Chery, Geely, Great Wall, Omoda/Jaecoo, Hyundai, MG, GAC, Mazda, Ford, Toyota, etc.) and filtering by ?brand=, ?type=, ?carline=, ?search=.',
  })
  @ApiStoreFilterQueries()
  public async getStore51(@Query() filterDto: FilterVehicleDto) {
    return this.vehiclesService.getVehiclesByStore('store51', filterDto);
  }

  // 6. Store 52 - Dandenong Nissan & Kia
  @Get(['stores/dandenong-nissan-kia', 'stores/dandenong-ni-ki', 'stores/store52', 'store52'])
  @ApiOperation({
    summary:
      'Store 52 - Dandenong Nissan & Kia vehicles (10 distinct makes in stock)',
    description:
      'Get inventory for Dandenong Nissan & Kia with multi-make support (Kia, Chery, Geely, Great Wall, Omoda/Jaecoo, Hyundai, GAC, Suzuki, etc.) and filtering by ?brand=, ?type=, ?carline=, ?search=.',
  })
  @ApiStoreFilterQueries()
  public async getStore52(@Query() filterDto: FilterVehicleDto) {
    return this.vehiclesService.getVehiclesByStore('store52', filterDto);
  }

  // 7. Store 70 - South Morang Kia
  @Get(['stores/south-morang-kia', 'stores/store70', 'store70'])
  @ApiOperation({
    summary: 'Store 70 - South Morang Kia vehicles (23 distinct makes in stock)',
    description:
      'Get inventory for South Morang Kia with multi-make support (Kia, Chery, BYD, Toyota, Mazda, Honda, Hyundai, Mitsubishi, Ford, VW, Volvo, etc.) and filtering by ?brand=, ?type=, ?carline=, ?search=.',
  })
  @ApiStoreFilterQueries()
  public async getStore70(@Query() filterDto: FilterVehicleDto) {
    return this.vehiclesService.getVehiclesByStore('store70', filterDto);
  }

  // 8. Store 90 - Berwick MG & Hyundai
  @Get(['stores/berwick-hyundai', 'stores/store90', 'store90'])
  @ApiOperation({
    summary:
      'Store 90 - Berwick MG & Hyundai vehicles (22 distinct makes in stock)',
    description:
      'Get inventory for Berwick MG & Hyundai with multi-make support (Hyundai, Chery, Toyota, Ford, Kia, Nissan, Mazda, MG, VW, Holden, etc.) and filtering by ?brand=, ?type=, ?carline=, ?search=.',
  })
  @ApiStoreFilterQueries()
  public async getStore90(@Query() filterDto: FilterVehicleDto) {
    return this.vehiclesService.getVehiclesByStore('store90', filterDto);
  }

  // Dynamic Store Endpoint
  @Get('stores/:identifier')
  @ApiOperation({
    summary: 'Get vehicles by store identifier / slug',
    description:
      'Fetch vehicles using store identifier (e.g. store01, cheltenham-kia, 40, south-morang-hyundai, etc.) with full multi-make filtering via ?brand=, ?type=, ?carline=, etc.',
  })
  @ApiStoreFilterQueries()
  public async getStoreByIdentifier(
    @Param('identifier') identifier: string,
    @Query() filterDto: FilterVehicleDto,
  ) {
    return this.vehiclesService.getVehiclesByStore(identifier, filterDto);
  }
}
