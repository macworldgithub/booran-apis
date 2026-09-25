import { NestFactory } from '@nestjs/core';
import { ValidationPipe, Logger } from '@nestjs/common';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { ConfigService } from '@nestjs/config';
import { AppModule } from './app.module';

async function bootstrap() {
  const logger = new Logger('Bootstrap');
  const app = await NestFactory.create(AppModule);

  // Enable CORS for client apps
  app.enableCors();

  // Enable validation and transformation
  app.useGlobalPipes(
    new ValidationPipe({
      transform: true,
      whitelist: true,
      transformOptions: { enableImplicitConversion: true },
    }),
  );

  // Swagger OpenAPI documentation
  const config = new DocumentBuilder()
    .setTitle('Booran Motors Dealerships API')
    .setDescription(
      'REST APIs for 6 Booran Motors dealership stores with New/Used vehicle filtering, search, and CSV sync.',
    )
    .setVersion('1.0.0')
    .addTag('Stores', 'Endpoints for each of the 6 dealership stores')
    .addTag('Vehicles', 'Global vehicle search and administrative sync')
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api/docs', app, document);

  const configService = app.get(ConfigService);
  const port = configService.get<number>('PORT', 3090);
  await app.listen(port);

  logger.log(`🚀 Server running at http://localhost:${port}`);
  logger.log(`📖 Swagger API Documentation available at http://localhost:${port}/api/docs`);
  logger.log(`🏬 Stores Overview available at http://localhost:${port}/api/stores`);
}
bootstrap();


