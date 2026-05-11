import { PrismaClient } from "../../src/generated/prisma";
import { PrismaPg } from "@prisma/adapter-pg";
import { readFileSync } from "fs";
import { join } from "path";

const adapter = new PrismaPg({ connectionString: process.env.DATABASE_URL! });
const prisma = new PrismaClient({ adapter });

interface CountySeed {
  name: string;
  fips: string;
  population: number;
}

async function main() {
  const countiesPath = join(__dirname, "counties.json");
  const raw = readFileSync(countiesPath, "utf-8");
  const counties: CountySeed[] = JSON.parse(raw);

  console.log(`Seeding ${counties.length} Michigan counties...`);

  let created = 0;
  let updated = 0;

  for (const county of counties) {
    const result = await prisma.county.upsert({
      where: { name: county.name },
      update: {
        fips: county.fips,
        population: county.population,
      },
      create: {
        name: county.name,
        fips: county.fips,
        population: county.population,
      },
    });

    // If updatedAt is close to createdAt, it was just created
    const isNew =
      result.updatedAt.getTime() - result.createdAt.getTime() < 1000;
    if (isNew) {
      created++;
    } else {
      updated++;
    }
  }

  console.log(
    `Seeding complete: ${created} created, ${updated} updated, ${counties.length} total counties.`,
  );
}

main()
  .catch((e) => {
    console.error("Seed failed:", e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
