export interface StoreMeta {
  storeId: string;
  storeNumber: string;
  name: string;
  slug: string;
  brand: 'Kia' | 'Hyundai';
  location: string;
}

export const STORES_MAP: Record<string, StoreMeta> = {
  store01: {
    storeId: 'store01',
    storeNumber: '01',
    name: 'Cheltenham Kia',
    slug: 'cheltenham-kia',
    brand: 'Kia',
    location: 'Cheltenham',
  },
  store20: {
    storeId: 'store20',
    storeNumber: '20',
    name: 'Cranbourne Hyundai',
    slug: 'cranbourne-hyundai',
    brand: 'Hyundai',
    location: 'Cranbourne',
  },
  store40: {
    storeId: 'store40',
    storeNumber: '40',
    name: 'South Morang Hyundai',
    slug: 'south-morang-hyundai',
    brand: 'Hyundai',
    location: 'South Morang',
  },
  store50: {
    storeId: 'store50',
    storeNumber: '50',
    name: 'Dandenong Hyundai',
    slug: 'dandenong-hyundai',
    brand: 'Hyundai',
    location: 'Dandenong',
  },
  store70: {
    storeId: 'store70',
    storeNumber: '70',
    name: 'South Morang Kia',
    slug: 'south-morang-kia',
    brand: 'Kia',
    location: 'South Morang',
  },
  store90: {
    storeId: 'store90',
    storeNumber: '90',
    name: 'Berwick Hyundai',
    slug: 'berwick-hyundai',
    brand: 'Hyundai',
    location: 'Berwick',
  },
};

export const STORES_LIST: StoreMeta[] = Object.values(STORES_MAP);

export function findStoreByIdentifier(identifier: string): StoreMeta | undefined {
  if (!identifier) return undefined;
  const normalized = identifier.toLowerCase().replace(/[^a-z0-9]/g, '');

  return STORES_LIST.find((store) => {
    const storeIdNorm = store.storeId.toLowerCase();
    const storeNumberNorm = store.storeNumber.toLowerCase();
    const slugNorm = store.slug.toLowerCase().replace(/[^a-z0-9]/g, '');
    const nameNorm = store.name.toLowerCase().replace(/[^a-z0-9]/g, '');

    return (
      identifier.toLowerCase() === store.storeId.toLowerCase() ||
      identifier.toLowerCase() === store.slug.toLowerCase() ||
      identifier.toLowerCase() === store.storeNumber.toLowerCase() ||
      normalized === storeIdNorm ||
      normalized === storeNumberNorm ||
      normalized === slugNorm ||
      normalized === nameNorm
    );
  });
}
