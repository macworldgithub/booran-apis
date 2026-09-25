import { ApiPropertyOptional } from '@nestjs/swagger';
import { IsOptional, IsIn, IsString, IsNumber, Min } from 'class-validator';
import { Type } from 'class-transformer';

export class FilterVehicleDto {
  @ApiPropertyOptional({
    description: 'Filter by vehicle type (new or used)',
    enum: ['new', 'used'],
    example: 'new',
  })
  @IsOptional()
  @IsIn(['new', 'used'])
  type?: 'new' | 'used';

  @ApiPropertyOptional({
    description: 'Filter by vehicle status (e.g. IN-STOCK, LOANER, WHOLESALE)',
    example: 'IN-STOCK',
  })
  @IsOptional()
  @IsString()
  status?: string;

  @ApiPropertyOptional({
    description: 'Filter by carline/model (e.g. CARNIVAL, SELTOS, TUCSON)',
    example: 'CARNIVAL',
  })
  @IsOptional()
  @IsString()
  carline?: string;

  @ApiPropertyOptional({
    description: 'Search across description, stockNumber, colour, regNo',
    example: 'GT-LINE',
  })
  @IsOptional()
  @IsString()
  search?: string;

  @ApiPropertyOptional({
    description: 'Filter by store identifier, slug, or number (for global vehicle query)',
    example: 'cheltenham-kia',
  })
  @IsOptional()
  @IsString()
  store?: string;

  @ApiPropertyOptional({
    description: 'Filter by brand (Kia or Hyundai)',
    example: 'Kia',
  })
  @IsOptional()
  @IsString()
  brand?: string;

  @ApiPropertyOptional({
    description: 'Sort field (e.g. listPrice, age, year, createdAt)',
    example: 'listPrice',
  })
  @IsOptional()
  @IsString()
  sort?: string;

  @ApiPropertyOptional({
    description: 'Sort order: asc or desc',
    enum: ['asc', 'desc'],
    example: 'asc',
  })
  @IsOptional()
  @IsIn(['asc', 'desc'])
  order?: 'asc' | 'desc';

  @ApiPropertyOptional({
    description: 'Pagination limit (defaults to returning all if omitted, or specify integer)',
    example: 50,
  })
  @IsOptional()
  @Type(() => Number)
  @IsNumber()
  @Min(1)
  limit?: number;

  @ApiPropertyOptional({
    description: 'Page number for pagination (1-indexed)',
    example: 1,
  })
  @IsOptional()
  @Type(() => Number)
  @IsNumber()
  @Min(1)
  page?: number;
}
