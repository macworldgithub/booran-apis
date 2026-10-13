import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { App } from 'supertest/types';
import { AppModule } from './../src/app.module';

describe('AppController (e2e)', () => {
  let app: INestApplication<App>;

  beforeEach(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();
  });

  it('/ (GET)', () => {
    return request(app.getHttpServer())
      .get('/')
      .expect(200)
      .expect('Hello World!');
  });

  it('/api/vehicles/stores-by-stock/P251203 (GET) returns all matching stores for P251203', async () => {
    const response = await request(app.getHttpServer())
      .get('/api/vehicles/stores-by-stock/P251203')
      .expect(200);

    expect(response.body.success).toBe(true);
    expect(response.body.stockNumber).toBe('P251203');
    expect(response.body.found).toBe(true);
    expect(response.body.totalStores).toBe(3);
    expect(response.body.stores).toEqual(
      expect.arrayContaining([
        'Dandenong Mitsubishi & Hyundai',
        'Cranbourne MG / Mitsubishi / Kia',
        'Dandenong Nissan & Kia',
      ]),
    );
  });

  it('/api/vehicles/stores-by-stock?stockNumber=P251203 (GET query param) returns all matching stores', async () => {
    const response = await request(app.getHttpServer())
      .get('/api/vehicles/stores-by-stock?stockNumber=P251203')
      .expect(200);

    expect(response.body.success).toBe(true);
    expect(response.body.stockNumber).toBe('P251203');
    expect(response.body.stores).toHaveLength(3);
  });

  afterAll(async () => {
    if (app) {
      await app.close();
    }
  });
});
