import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { Vehicle, VehicleDocument } from '../schemas/vehicle.schema';
import { FilterVehicleDto } from '../dto/filter-vehicle.dto';
import {
  findStoreByIdentifier,
  StoreMeta,
  STORES_LIST,
} from '../../config/stores.config';

export interface PaginatedResult<T> {
  success: boolean;
  store?: StoreMeta;
  filters: Partial<FilterVehicleDto>;
  total: number;
  count: number;
  page?: number;
  totalPages?: number;
  data: T[];
}

export interface StoreSummary {
  storeId: string;
  storeNumber: string;
  name: string;
  slug: string;
  brand: string;
  location: string;
  totalVehicles: number;
  newVehicles: number;
  usedVehicles: number;
  apiEndpoint: string;
}

@Injectable()
export class VehiclesService {
  constructor(
    @InjectModel(Vehicle.name)
    private readonly vehicleModel: Model<VehicleDocument>,
  ) {}

  /**
   * Build MongoDB query filter from FilterVehicleDto
   */
  private buildQueryFilter(
    filterDto: FilterVehicleDto,
    store?: StoreMeta,
  ): Record<string, any> {
    const query: Record<string, any> = {};

    if (store) {
      query.storeId = store.storeId;
    } else if (filterDto.store) {
      const matchedStore = findStoreByIdentifier(filterDto.store);
      if (matchedStore) {
        query.storeId = matchedStore.storeId;
      } else {
        query.$or = [
          { storeId: filterDto.store },
          { storeSlug: filterDto.store },
          { storeNumber: filterDto.store },
        ];
      }
    }

    if (filterDto.type) {
      query.type = filterDto.type;
    }

    if (filterDto.status) {
      query.status = new RegExp(`^${filterDto.status.trim()}$`, 'i');
    }

    if (filterDto.carline) {
      query.carline = new RegExp(`^${filterDto.carline.trim()}$`, 'i');
    }

    if (filterDto.brand) {
      query.brand = new RegExp(`^${filterDto.brand.trim()}$`, 'i');
    }

    if (filterDto.search) {
      const searchRegex = new RegExp(filterDto.search.trim(), 'i');
      query.$or = [
        { stockNumber: searchRegex },
        { description: searchRegex },
        { carline: searchRegex },
        { colour: searchRegex },
        { regNo: searchRegex },
      ];
    }

    return query;
  }

  /**
   * Get vehicles for a specific store (identified by storeId, slug, or number)
   */
  public async getVehiclesByStore(
    identifier: string,
    filterDto: FilterVehicleDto,
  ): Promise<PaginatedResult<Vehicle>> {
    const store = findStoreByIdentifier(identifier);
    if (!store) {
      throw new NotFoundException(
        `Store with identifier '${identifier}' not found. Available stores: ${STORES_LIST.map((s) => s.slug).join(', ')}`,
      );
    }

    const query = this.buildQueryFilter(filterDto, store);
    return this.executeQuery(query, filterDto, store);
  }

  /**
   * Get vehicles across all stores with optional filters
   */
  public async getAllVehicles(
    filterDto: FilterVehicleDto,
  ): Promise<PaginatedResult<Vehicle>> {
    const query = this.buildQueryFilter(filterDto);
    return this.executeQuery(query, filterDto);
  }

  /**
   * Execute query with sorting, pagination, and count
   */
  private async executeQuery(
    query: Record<string, any>,
    filterDto: FilterVehicleDto,
    store?: StoreMeta,
  ): Promise<PaginatedResult<Vehicle>> {
    const total = await this.vehicleModel.countDocuments(query).exec();

    let queryBuilder = this.vehicleModel.find(query);

    // Sorting
    const sortField = filterDto.sort || 'createdAt';
    const sortOrder = filterDto.order === 'asc' ? 1 : -1;
    queryBuilder = queryBuilder.sort({ [sortField]: sortOrder, _id: 1 });

    // Pagination (if specified)
    let page: number | undefined;
    let totalPages: number | undefined;

    if (filterDto.limit) {
      const limit = Math.max(1, filterDto.limit);
      page = Math.max(1, filterDto.page || 1);
      const skip = (page - 1) * limit;
      queryBuilder = queryBuilder.skip(skip).limit(limit);
      totalPages = Math.ceil(total / limit);
    }

    const data = await queryBuilder.lean().exec();

    return {
      success: true,
      store,
      filters: {
        type: filterDto.type,
        status: filterDto.status,
        carline: filterDto.carline,
        brand: filterDto.brand,
        search: filterDto.search,
      },
      total,
      count: data.length,
      page,
      totalPages,
      data: data as unknown as Vehicle[],
    };
  }

  /**
   * Get single vehicle by stock number
   */
  public async getVehicleByStock(
    stockNumber: string,
    storeId?: string,
  ): Promise<Vehicle> {
    const filter: Record<string, any> = { stockNumber };
    if (storeId) {
      filter.storeId = storeId;
    }

    const vehicle = await this.vehicleModel.findOne(filter).lean().exec();
    if (!vehicle) {
      throw new NotFoundException(
        `Vehicle with stock number '${stockNumber}' not found`,
      );
    }
    return vehicle as unknown as Vehicle;
  }

  /**
   * Get overview / statistics for all 6 stores
   */
  public async getStoresOverview(): Promise<{
    success: boolean;
    totalStores: number;
    stores: StoreSummary[];
  }> {
    const aggregations = await this.vehicleModel.aggregate([
      {
        $group: {
          _id: { storeId: '$storeId', type: '$type' },
          count: { $sum: 1 },
        },
      },
    ]);

    const countsMap = new Map<string, { new: number; used: number }>();

    for (const item of aggregations) {
      const { storeId, type } = item._id;
      if (!countsMap.has(storeId)) {
        countsMap.set(storeId, { new: 0, used: 0 });
      }
      const entry = countsMap.get(storeId)!;
      if (type === 'new') entry.new += item.count;
      if (type === 'used') entry.used += item.count;
    }

    const stores: StoreSummary[] = STORES_LIST.map((store) => {
      const counts = countsMap.get(store.storeId) || { new: 0, used: 0 };
      return {
        storeId: store.storeId,
        storeNumber: store.storeNumber,
        name: store.name,
        slug: store.slug,
        brand: store.brand,
        location: store.location,
        totalVehicles: counts.new + counts.used,
        newVehicles: counts.new,
        usedVehicles: counts.used,
        apiEndpoint: `/api/stores/${store.slug}`,
      };
    });

    return {
      success: true,
      totalStores: stores.length,
      stores,
    };
  }
}
