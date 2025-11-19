"""
Django management command untuk populate dummy data Udang Tracker
Simpan file ini di: tracker/management/commands/populate_dummy_data.py

Usage: python manage.py populate_dummy_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import random
from decimal import Decimal

from tracker.models import (
    Node, Farm, Lot, LotMovement, PondLog, 
    Sampling, LabTest, Document, Incident, IncidentRelatedLot
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate database dengan 100 lot dummy data untuk testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear semua data sebelum populate (HATI-HATI!)',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Menghapus semua data...'))
            self.clear_data()
        
        self.stdout.write(self.style.SUCCESS('Mulai generate dummy data...'))
        
        # Create user if not exists
        user = self.create_user()
        
        # Create Nodes
        nodes = self.create_nodes()
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(nodes)} nodes'))
        
        # Create Farms
        farms = self.create_farms(nodes)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(farms)} farms'))
        
        # Create Lots (100 lots)
        lots = self.create_lots(user, farms)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(lots)} lots'))
        
        # Create Lot Movements
        movements = self.create_lot_movements(lots, nodes)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(movements)} movements'))
        
        # Create Pond Logs
        pond_logs = self.create_pond_logs(farms)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(pond_logs)} pond logs'))
        
        # Create Samplings & Lab Tests
        samplings, lab_tests = self.create_samplings_and_tests(lots)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(samplings)} samplings'))
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(lab_tests)} lab tests'))
        
        # Create Documents
        documents = self.create_documents(farms, lots)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(documents)} documents'))
        
        # Create Incidents
        incidents = self.create_incidents(lots)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(incidents)} incidents'))
        
        self.stdout.write(self.style.SUCCESS('\n=== SUMMARY ==='))
        self.stdout.write(self.style.SUCCESS(f'Total Nodes: {len(nodes)}'))
        self.stdout.write(self.style.SUCCESS(f'Total Farms: {len(farms)}'))
        self.stdout.write(self.style.SUCCESS(f'Total Lots: {len(lots)}'))
        self.stdout.write(self.style.SUCCESS(f'Total Movements: {len(movements)}'))
        self.stdout.write(self.style.SUCCESS(f'Total Incidents: {len(incidents)}'))
        self.stdout.write(self.style.SUCCESS('\n✅ Dummy data berhasil di-populate!'))

    def clear_data(self):
        """Clear all data - USE WITH CAUTION!"""
        IncidentRelatedLot.objects.all().delete()
        Incident.objects.all().delete()
        Document.objects.all().delete()
        LabTest.objects.all().delete()
        Sampling.objects.all().delete()
        PondLog.objects.all().delete()
        LotMovement.objects.all().delete()
        Lot.objects.all().delete()
        Farm.objects.all().delete()
        Node.objects.all().delete()

    def create_user(self):
        """Create or get demo user"""
        user, created = User.objects.get_or_create(
            username='demo',
            defaults={
                'email': 'demo@udangtracker.com',
                'first_name': 'Demo',
                'last_name': 'User',
            }
        )
        if created:
            user.set_password('demo123')
            user.save()
        return user

    def create_nodes(self):
        """Create supply chain nodes"""
        nodes_data = [
            # Collectors
            ("Pengumpul Jaya", "COLLECTOR"),
            ("Pengumpul Sentosa", "COLLECTOR"),
            ("Pengumpul Makmur", "COLLECTOR"),
            ("Pengumpul Bahari", "COLLECTOR"),
            ("Pengumpul Nusantara", "COLLECTOR"),
            
            # Processors
            ("PT Sumber Jaya Processing", "PROCESSOR"),
            ("PT Mandiri Seafood", "PROCESSOR"),
            ("PT Bahari Prima", "PROCESSOR"),
            ("PT Ocean Fresh", "PROCESSOR"),
            ("PT Sentosa Marine", "PROCESSOR"),
            
            # Exporters
            ("PT Global Shrimp Export", "EXPORTER"),
            ("PT Indo Marine Export", "EXPORTER"),
            ("PT Nusantara Seafood", "EXPORTER"),
            ("PT Asia Pacific Shrimp", "EXPORTER"),
        ]
        
        nodes = []
        for name, node_type in nodes_data:
            node, _ = Node.objects.get_or_create(
                name=name,
                type=node_type
            )
            nodes.append(node)
        
        return nodes

    def create_farms(self, nodes):
        """Create farms with realistic data"""
        locations = [
            "Sidoarjo, Jawa Timur",
            "Gresik, Jawa Timur",
            "Lampung Selatan, Lampung",
            "Tuban, Jawa Timur",
            "Brebes, Jawa Tengah",
            "Kendal, Jawa Tengah",
            "Demak, Jawa Tengah",
            "Pati, Jawa Tengah",
            "Banyuwangi, Jawa Timur",
            "Situbondo, Jawa Timur",
        ]
        
        farm_names = [
            "Tambak Jaya Abadi",
            "Tambak Sentosa Mulya",
            "Tambak Makmur Sejahtera",
            "Tambak Bahari Nusantara",
            "Tambak Mina Lestari",
            "Tambak Rejeki Nusantara",
            "Tambak Sumber Rezeki",
            "Tambak Putra Mandiri",
            "Tambak Karya Utama",
            "Tambak Berkah Jaya",
            "Tambak Tirta Bahari",
            "Tambak Laut Biru",
            "Tambak Samudra Jaya",
            "Tambak Pantai Indah",
            "Tambak Bintang Laut",
        ]
        
        owners = [
            "Budi Santoso",
            "Ahmad Wijaya",
            "Siti Rahayu",
            "Hendra Kusuma",
            "Dewi Lestari",
            "Agus Priyanto",
            "Nur Hidayah",
            "Bambang Sutopo",
            "Ratna Sari",
            "Eko Prasetyo",
        ]
        
        farms = []
        for i in range(15):
            # Create farm node first
            farm_node = Node.objects.create(
                name=farm_names[i],
                type="FARM"
            )
            
            farm = Farm.objects.create(
                node=farm_node,
                name=farm_names[i],
                location=random.choice(locations),
                owner_name=random.choice(owners)
            )
            farms.append(farm)
        
        return farms

    def create_lots(self, user, farms):
        """Create 100 lots with realistic distribution"""
        lots = []
        base_date = timezone.now() - timedelta(days=180)  # 6 months ago
        
        # Distribution: 75% OK, 15% HOLD, 10% INVESTIGATE
        statuses = (
            ['OK'] * 75 + 
            ['HOLD'] * 15 + 
            ['INVESTIGATE'] * 10
        )
        random.shuffle(statuses)
        
        kontaminasi_types = [
            'Cesium tinggi',
            'Timbal (Pb) melebihi batas',
            'Kadmium terdeteksi',
            'Merkuri tinggi',
            'TPC melebihi standar',
            'Salmonella terdeteksi',
            'E.coli positif',
            'Antibiotik terdeteksi',
            'Formalin terdeteksi',
            'Warna tidak normal',
        ]
        
        for i in range(100):
            lot_num = str(i + 1).zfill(4)
            lot_id = f"LOT-2024-{lot_num}"
            
            status = statuses[i]
            farm = random.choice(farms)
            
            # Risk score distribution based on status
            if status == 'OK':
                risk_score = random.randint(0, 40)
                risk_level = 'LOW'
            elif status == 'HOLD':
                risk_score = random.randint(41, 70)
                risk_level = 'MEDIUM'
            else:  # INVESTIGATE
                risk_score = random.randint(71, 100)
                risk_level = 'HIGH'
            
            # Harvest date in last 6 months
            days_ago = random.randint(1, 180)
            harvest_date = (base_date + timedelta(days=days_ago)).date()
            
            # Volume varies
            volume = round(random.uniform(500, 3000), 2)
            
            lot = Lot.objects.create(
                lot_id=lot_id,
                creator=user,
                farm=farm,
                harvest_date=harvest_date,
                volume_kg=volume,
                status=status,
                jenis_kontaminasi=random.choice(kontaminasi_types) if status != 'OK' else '',
                risk_score=risk_score,
                risk_level=risk_level,
            )
            lots.append(lot)
        
        return lots

    def create_lot_movements(self, lots, nodes):
        """Create supply chain movements for lots"""
        collectors = [n for n in nodes if n.type == 'COLLECTOR']
        processors = [n for n in nodes if n.type == 'PROCESSOR']
        exporters = [n for n in nodes if n.type == 'EXPORTER']
        
        movements = []
        
        for lot in lots:
            base_time = timezone.make_aware(
                datetime.combine(lot.harvest_date, datetime.min.time())
            )
            
            # Movement 1: Farm -> Collector (day 0-1)
            movements.append(LotMovement.objects.create(
                lot=lot,
                node=random.choice(collectors),
                timestamp=base_time + timedelta(hours=random.randint(6, 24)),
                location=lot.farm.location,
                quantity_kg=lot.volume_kg
            ))
            
            # Movement 2: Collector -> Processor (day 1-3)
            movements.append(LotMovement.objects.create(
                lot=lot,
                node=random.choice(processors),
                timestamp=base_time + timedelta(days=1, hours=random.randint(0, 48)),
                quantity_kg=lot.volume_kg * random.uniform(0.85, 0.95)  # some loss
            ))
            
            # Movement 3: Processor -> Exporter (day 3-7) - only for OK lots
            if lot.status == 'OK' and random.random() > 0.3:
                movements.append(LotMovement.objects.create(
                    lot=lot,
                    node=random.choice(exporters),
                    timestamp=base_time + timedelta(days=3, hours=random.randint(0, 96)),
                    quantity_kg=lot.volume_kg * random.uniform(0.75, 0.85)
                ))
        
        return movements

    def create_pond_logs(self, farms):
        """Create pond logs for farms"""
        logs = []
        base_date = timezone.now() - timedelta(days=180)
        
        for farm in farms:
            # Create 20-40 logs per farm
            num_logs = random.randint(20, 40)
            
            for i in range(num_logs):
                log_date = (base_date + timedelta(days=random.randint(0, 180))).date()
                
                logs.append(PondLog.objects.create(
                    farm=farm,
                    date=log_date,
                    ph=round(random.uniform(7.0, 8.5), 2),
                    temperature_c=round(random.uniform(26.0, 32.0), 1),
                    salinity_ppt=round(random.uniform(15.0, 30.0), 1),
                    feed_type=random.choice(['Pelet Komersial', 'Pelet Khusus', 'Natural Feed']),
                    chemicals_used=random.choice(['Probiotik', 'Kapur', 'Tidak ada', 'Vitamin C']),
                    notes=random.choice([
                        'Kondisi normal',
                        'Udang aktif',
                        'Warna air sedikit keruh',
                        'Pemberian pakan optimal',
                        ''
                    ])
                ))
        
        return logs

    def create_samplings_and_tests(self, lots):
        """Create samplings and lab tests"""
        samplings = []
        lab_tests = []
        
        # Sample 60% of lots
        sampled_lots = random.sample(lots, k=60)
        
        test_parameters = [
            ('Cesium-137', 'Bq/kg', 100),
            ('Timbal (Pb)', 'ppm', 0.5),
            ('Kadmium (Cd)', 'ppm', 0.1),
            ('Merkuri (Hg)', 'ppm', 0.5),
            ('TPC', 'CFU/g', 1000000),
            ('Salmonella', 'MPN/g', 0),
            ('E.coli', 'MPN/g', 3),
        ]
        
        for lot in sampled_lots:
            # Create sampling
            sampling_date = lot.harvest_date + timedelta(days=random.randint(1, 5))
            
            sampling = Sampling.objects.create(
                lot=lot,
                date=sampling_date,
                location=lot.farm.location if lot.farm else 'Unknown',
                requested_by='Quality Control Team',
                status=random.choice(['SAMPLED', 'SENT_TO_LAB'])
            )
            samplings.append(sampling)
            
            # Create 3-5 lab tests per sampling
            num_tests = random.randint(3, 5)
            selected_params = random.sample(test_parameters, k=num_tests)
            
            for param_name, unit, limit in selected_params:
                # Determine if test passes or fails based on lot status
                if lot.status == 'OK':
                    value = random.uniform(0, limit * 0.8)  # Well below limit
                    result = 'PASS'
                elif lot.status == 'HOLD':
                    value = random.uniform(limit * 0.85, limit * 1.1)  # Near or slightly above
                    result = 'FAIL' if value > limit else 'PASS'
                else:  # INVESTIGATE
                    value = random.uniform(limit * 1.1, limit * 2.0)  # Significantly above
                    result = 'FAIL'
                
                lab_tests.append(LabTest.objects.create(
                    sampling=sampling,
                    parameter=param_name,
                    value=round(value, 3),
                    unit=unit,
                    limit_value=limit,
                    result=result
                ))
        
        return samplings, lab_tests

    def create_documents(self, farms, lots):
        """Create documents for farms and lots"""
        documents = []
        
        # Farm documents (2-3 per farm)
        for farm in farms[:10]:  # First 10 farms
            for _ in range(random.randint(2, 3)):
                doc_type = random.choice(['FARM_CERT', 'LAB_CERT'])
                issue_date = (timezone.now() - timedelta(days=random.randint(30, 365))).date()
                
                documents.append(Document.objects.create(
                    doc_type=doc_type,
                    title=f"Sertifikat {farm.name} - {issue_date.year}",
                    farm=farm,
                    issued_by=random.choice(['BPOM', 'Kementerian KKP', 'ISO Certification']),
                    issue_date=issue_date,
                    expiry_date=issue_date + timedelta(days=365)
                ))
        
        # Lot documents (for problematic lots)
        problematic_lots = [l for l in lots if l.status in ['HOLD', 'INVESTIGATE']]
        for lot in problematic_lots[:15]:  # First 15 problematic lots
            documents.append(Document.objects.create(
                doc_type='LAB_CERT',
                title=f"Lab Test Result - {lot.lot_id}",
                lot=lot,
                issued_by='Lab Uji Standar',
                issue_date=lot.harvest_date + timedelta(days=3)
            ))
        
        return documents

    def create_incidents(self, lots):
        """Create incidents for problematic lots"""
        incidents = []
        problematic_lots = [l for l in lots if l.status in ['HOLD', 'INVESTIGATE']]
        
        # Create incidents for 40% of problematic lots
        incident_lots = random.sample(problematic_lots, k=min(10, len(problematic_lots)))
        
        descriptions = [
            'Lot ditolak oleh buyer karena hasil lab tidak memenuhi standar.',
            'Kontaminasi terdeteksi saat inspeksi rutin.',
            'Buyer melaporkan kualitas tidak sesuai spesifikasi.',
            'Hasil uji lab menunjukkan parameter melebihi batas aman.',
            'Penolakan ekspor karena dokumen tidak lengkap dan hasil lab buruk.',
        ]
        
        for lot in incident_lots:
            incident_type = random.choice(['EXPORT_REJECT', 'LAB_FAIL', 'COMPLAINT'])
            
            incident = Incident.objects.create(
                lot=lot,
                incident_type=incident_type,
                description=random.choice(descriptions),
                date=lot.harvest_date + timedelta(days=random.randint(5, 15)),
                status=random.choice(['OPEN', 'IN_PROGRESS', 'CLOSED'])
            )
            incidents.append(incident)
            
            # Link related lots (1-3 related lots)
            other_lots = [l for l in problematic_lots if l != lot]
            related = random.sample(other_lots, k=min(random.randint(1, 3), len(other_lots)))
            
            for related_lot in related:
                IncidentRelatedLot.objects.create(
                    incident=incident,
                    lot=related_lot
                )
        
        return incidents