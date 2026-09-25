import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';

export type VehicleDocument = HydratedDocument<Vehicle>;

@Schema({ timestamps: true, collection: 'vehicles' })
export class Vehicle {
  @Prop({ type: String, required: true, index: true })
  storeId: string; // e.g. 'store01'

  @Prop({ type: String, required: true, index: true })
  storeNumber: string; // e.g. '01'

  @Prop({ type: String, required: true })
  storeName: string; // e.g. 'Cheltenham Kia'

  @Prop({ type: String, required: true, index: true })
  storeSlug: string; // e.g. 'cheltenham-kia'

  @Prop({ type: String, required: true, index: true })
  brand: string; // 'Kia' | 'Hyundai'

  @Prop({ type: String, required: true, enum: ['new', 'used'], index: true })
  type: 'new' | 'used';

  @Prop({ type: String, required: true, index: true })
  stockNumber: string; // e.g. '428982', 'S0114058'

  @Prop({ type: String, default: '', index: true })
  carline: string; // e.g. 'CARNIVAL', 'SELTOS'

  @Prop({ type: String, default: '' })
  description: string;

  @Prop({ type: String, default: '' })
  colour: string;

  @Prop({ type: String, default: '' })
  location: string;

  @Prop({ type: String, default: '' })
  destLocation: string;

  @Prop({ type: Number, default: null, index: true })
  listPrice: number | null;

  @Prop({ type: Number, default: null })
  age: number | null;

  @Prop({ type: String, default: '', index: true })
  status: string; // e.g. 'LOANER', 'IN-STOCK', 'WHOLESALE'

  @Prop({ type: String, default: '' })
  openRoPo: string; // 'Y' | 'N'

  // New vehicle specific fields
  @Prop({ type: String, default: null })
  fa: string | null;

  @Prop({ type: String, default: null })
  deal: string | null;

  // Used vehicle specific fields
  @Prop({ type: Number, default: null, index: true })
  year: number | null; // normalized 4-digit year, e.g. 2024

  @Prop({ type: String, default: null })
  originalYear: string | null; // original raw string, e.g. '24'

  @Prop({ type: String, default: null })
  regNo: string | null;

  @Prop({ type: Number, default: null, index: true })
  odometer: number | null;

  @Prop({ type: String, default: '' })
  sourceFile: string;
}

export const VehicleSchema = SchemaFactory.createForClass(Vehicle);

// Compound indexes for optimal performance
VehicleSchema.index({ storeId: 1, stockNumber: 1 }, { unique: true });
VehicleSchema.index({ storeId: 1, type: 1 });
VehicleSchema.index({ storeSlug: 1, type: 1 });
VehicleSchema.index({ storeNumber: 1, type: 1 });
VehicleSchema.index({ brand: 1, type: 1 });
