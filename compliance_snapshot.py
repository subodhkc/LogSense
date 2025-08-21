"""
compliance_snapshot.py - Forensic snapshot module with hash-linking
Patent Implementation: Claims 1f, 3, 10 - Merkle tree-based audit trail
"""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
import threading

@dataclass
class ForensicSnapshot:
    snapshot_id: str
    session_id: str
    timestamp: datetime
    previous_hash: Optional[str]
    current_hash: str
    diagnostic_input: Dict[str, Any]
    engine_sequence: List[str]
    outputs_and_scores: List[Dict[str, Any]]
    traceability_tag: str
    compliance_metadata: Dict[str, Any]
    merkle_root: Optional[str] = None

@dataclass
class AuditChain:
    chain_id: str
    genesis_hash: str
    current_head: str
    total_snapshots: int
    created_at: datetime
    last_updated: datetime

class ComplianceSnapshotModule:
    """
    Forensic snapshot module with cryptographic hash-linking and audit trail
    Implements patent claims for compliance-aware traceability
    """
    
    def __init__(self, storage_path: str = "compliance_audit.db"):
        self.storage_path = storage_path
        self.lock = threading.Lock()
        self.current_chain: Optional[AuditChain] = None
        self._initialize_storage()
        self._load_or_create_chain()
    
    def _initialize_storage(self):
        """Initialize SQLite database for audit storage"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        # Create snapshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS forensic_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                previous_hash TEXT,
                current_hash TEXT NOT NULL,
                diagnostic_input TEXT NOT NULL,
                engine_sequence TEXT NOT NULL,
                outputs_and_scores TEXT NOT NULL,
                traceability_tag TEXT NOT NULL,
                compliance_metadata TEXT NOT NULL,
                merkle_root TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Create audit chains table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_chains (
                chain_id TEXT PRIMARY KEY,
                genesis_hash TEXT NOT NULL,
                current_head TEXT NOT NULL,
                total_snapshots INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                last_updated TEXT NOT NULL
            )
        ''')
        
        # Create hash index for fast lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_snapshot_hash 
            ON forensic_snapshots(current_hash)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_id 
            ON forensic_snapshots(session_id)
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_or_create_chain(self):
        """Load existing audit chain or create new one"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM audit_chains ORDER BY created_at DESC LIMIT 1')
        result = cursor.fetchone()
        
        if result:
            self.current_chain = AuditChain(
                chain_id=result[0],
                genesis_hash=result[1],
                current_head=result[2],
                total_snapshots=result[3],
                created_at=datetime.fromisoformat(result[4]),
                last_updated=datetime.fromisoformat(result[5])
            )
        else:
            # Create genesis chain
            genesis_hash = self._calculate_genesis_hash()
            chain_id = str(uuid.uuid4())
            now = datetime.now()
            
            self.current_chain = AuditChain(
                chain_id=chain_id,
                genesis_hash=genesis_hash,
                current_head=genesis_hash,
                total_snapshots=0,
                created_at=now,
                last_updated=now
            )
            
            cursor.execute('''
                INSERT INTO audit_chains 
                (chain_id, genesis_hash, current_head, total_snapshots, created_at, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                self.current_chain.chain_id,
                self.current_chain.genesis_hash,
                self.current_chain.current_head,
                self.current_chain.total_snapshots,
                self.current_chain.created_at.isoformat(),
                self.current_chain.last_updated.isoformat()
            ))
            conn.commit()
        
        conn.close()
    
    def create_forensic_snapshot(
        self,
        session_id: str,
        diagnostic_input: Dict[str, Any],
        engine_sequence: List[str],
        outputs_and_scores: List[Dict[str, Any]],
        traceability_tag: str,
        compliance_tags: List[str] = None
    ) -> ForensicSnapshot:
        """
        Create a new forensic snapshot with hash-linking
        """
        with self.lock:
            snapshot_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            # Prepare compliance metadata
            compliance_metadata = {
                'compliance_tags': compliance_tags or [],
                'retention_policy': 'standard',
                'classification': 'internal',
                'audit_level': 'full',
                'chain_position': self.current_chain.total_snapshots + 1
            }
            
            # Create snapshot data for hashing
            snapshot_data = {
                'snapshot_id': snapshot_id,
                'session_id': session_id,
                'timestamp': timestamp.isoformat(),
                'diagnostic_input': diagnostic_input,
                'engine_sequence': engine_sequence,
                'outputs_and_scores': outputs_and_scores,
                'traceability_tag': traceability_tag,
                'compliance_metadata': compliance_metadata
            }
            
            # Calculate current hash
            current_hash = self._calculate_snapshot_hash(snapshot_data, self.current_chain.current_head)
            
            # Calculate Merkle root for this snapshot
            merkle_root = self._calculate_merkle_root([current_hash])
            
            # Create snapshot object
            snapshot = ForensicSnapshot(
                snapshot_id=snapshot_id,
                session_id=session_id,
                timestamp=timestamp,
                previous_hash=self.current_chain.current_head,
                current_hash=current_hash,
                diagnostic_input=diagnostic_input,
                engine_sequence=engine_sequence,
                outputs_and_scores=outputs_and_scores,
                traceability_tag=traceability_tag,
                compliance_metadata=compliance_metadata,
                merkle_root=merkle_root
            )
            
            # Store snapshot
            self._store_snapshot(snapshot)
            
            # Update chain
            self._update_chain_head(current_hash)
            
            return snapshot
    
    def _calculate_snapshot_hash(self, snapshot_data: Dict[str, Any], previous_hash: str) -> str:
        """Calculate SHA-256 hash for snapshot with previous hash linking"""
        # Create deterministic JSON representation
        json_data = json.dumps(snapshot_data, sort_keys=True, default=str)
        
        # Combine with previous hash for chaining
        combined_data = f"{previous_hash}:{json_data}"
        
        return hashlib.sha256(combined_data.encode('utf-8')).hexdigest()
    
    def _calculate_genesis_hash(self) -> str:
        """Calculate genesis hash for new audit chain"""
        genesis_data = {
            'type': 'genesis',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0',
            'purpose': 'SKC Log Analyzer Audit Chain'
        }
        
        json_data = json.dumps(genesis_data, sort_keys=True)
        return hashlib.sha256(json_data.encode('utf-8')).hexdigest()
    
    def _calculate_merkle_root(self, hashes: List[str]) -> str:
        """Calculate Merkle root for given hashes"""
        if not hashes:
            return ""
        
        if len(hashes) == 1:
            return hashes[0]
        
        # Pad to even number
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])
        
        # Calculate parent level
        parent_hashes = []
        for i in range(0, len(hashes), 2):
            combined = f"{hashes[i]}:{hashes[i+1]}"
            parent_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
            parent_hashes.append(parent_hash)
        
        # Recursively calculate root
        return self._calculate_merkle_root(parent_hashes)
    
    def _store_snapshot(self, snapshot: ForensicSnapshot):
        """Store snapshot in database"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO forensic_snapshots 
            (snapshot_id, session_id, timestamp, previous_hash, current_hash,
             diagnostic_input, engine_sequence, outputs_and_scores, 
             traceability_tag, compliance_metadata, merkle_root, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            snapshot.snapshot_id,
            snapshot.session_id,
            snapshot.timestamp.isoformat(),
            snapshot.previous_hash,
            snapshot.current_hash,
            json.dumps(snapshot.diagnostic_input, default=str),
            json.dumps(snapshot.engine_sequence),
            json.dumps(snapshot.outputs_and_scores, default=str),
            snapshot.traceability_tag,
            json.dumps(snapshot.compliance_metadata),
            snapshot.merkle_root,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _update_chain_head(self, new_hash: str):
        """Update audit chain with new head"""
        self.current_chain.current_head = new_hash
        self.current_chain.total_snapshots += 1
        self.current_chain.last_updated = datetime.now()
        
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE audit_chains 
            SET current_head = ?, total_snapshots = ?, last_updated = ?
            WHERE chain_id = ?
        ''', (
            self.current_chain.current_head,
            self.current_chain.total_snapshots,
            self.current_chain.last_updated.isoformat(),
            self.current_chain.chain_id
        ))
        
        conn.commit()
        conn.close()
    
    def verify_chain_integrity(self) -> Dict[str, Any]:
        """Verify integrity of the entire audit chain"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT snapshot_id, previous_hash, current_hash, diagnostic_input,
                   engine_sequence, outputs_and_scores, traceability_tag,
                   compliance_metadata, timestamp, session_id
            FROM forensic_snapshots 
            ORDER BY timestamp ASC
        ''')
        
        snapshots = cursor.fetchall()
        conn.close()
        
        verification_result = {
            'is_valid': True,
            'total_snapshots': len(snapshots),
            'broken_links': [],
            'hash_mismatches': [],
            'verification_timestamp': datetime.now().isoformat()
        }
        
        expected_previous_hash = self.current_chain.genesis_hash
        
        for i, snapshot_row in enumerate(snapshots):
            snapshot_id, previous_hash, current_hash = snapshot_row[0], snapshot_row[1], snapshot_row[2]
            
            # Verify hash linking
            if previous_hash != expected_previous_hash:
                verification_result['is_valid'] = False
                verification_result['broken_links'].append({
                    'snapshot_id': snapshot_id,
                    'expected_previous': expected_previous_hash,
                    'actual_previous': previous_hash,
                    'position': i
                })
            
            # Verify hash calculation
            snapshot_data = {
                'snapshot_id': snapshot_id,
                'session_id': snapshot_row[9],
                'timestamp': snapshot_row[8],
                'diagnostic_input': json.loads(snapshot_row[3]),
                'engine_sequence': json.loads(snapshot_row[4]),
                'outputs_and_scores': json.loads(snapshot_row[5]),
                'traceability_tag': snapshot_row[6],
                'compliance_metadata': json.loads(snapshot_row[7])
            }
            
            calculated_hash = self._calculate_snapshot_hash(snapshot_data, previous_hash)
            
            if calculated_hash != current_hash:
                verification_result['is_valid'] = False
                verification_result['hash_mismatches'].append({
                    'snapshot_id': snapshot_id,
                    'expected_hash': calculated_hash,
                    'actual_hash': current_hash,
                    'position': i
                })
            
            expected_previous_hash = current_hash
        
        return verification_result
    
    def get_snapshot_by_id(self, snapshot_id: str) -> Optional[ForensicSnapshot]:
        """Retrieve specific snapshot by ID"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM forensic_snapshots WHERE snapshot_id = ?
        ''', (snapshot_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        return ForensicSnapshot(
            snapshot_id=result[0],
            session_id=result[1],
            timestamp=datetime.fromisoformat(result[2]),
            previous_hash=result[3],
            current_hash=result[4],
            diagnostic_input=json.loads(result[5]),
            engine_sequence=json.loads(result[6]),
            outputs_and_scores=json.loads(result[7]),
            traceability_tag=result[8],
            compliance_metadata=json.loads(result[9]),
            merkle_root=result[10]
        )
    
    def get_session_snapshots(self, session_id: str) -> List[ForensicSnapshot]:
        """Get all snapshots for a specific session"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM forensic_snapshots 
            WHERE session_id = ? 
            ORDER BY timestamp ASC
        ''', (session_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        snapshots = []
        for result in results:
            snapshot = ForensicSnapshot(
                snapshot_id=result[0],
                session_id=result[1],
                timestamp=datetime.fromisoformat(result[2]),
                previous_hash=result[3],
                current_hash=result[4],
                diagnostic_input=json.loads(result[5]),
                engine_sequence=json.loads(result[6]),
                outputs_and_scores=json.loads(result[7]),
                traceability_tag=result[8],
                compliance_metadata=json.loads(result[9]),
                merkle_root=result[10]
            )
            snapshots.append(snapshot)
        
        return snapshots
    
    def export_audit_report(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Export comprehensive audit report"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        # Build query with date filters
        query = 'SELECT * FROM forensic_snapshots'
        params = []
        
        if start_date or end_date:
            query += ' WHERE '
            conditions = []
            
            if start_date:
                conditions.append('timestamp >= ?')
                params.append(start_date.isoformat())
            
            if end_date:
                conditions.append('timestamp <= ?')
                params.append(end_date.isoformat())
            
            query += ' AND '.join(conditions)
        
        query += ' ORDER BY timestamp ASC'
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        # Verify chain integrity
        integrity_check = self.verify_chain_integrity()
        
        # Generate report
        report = {
            'report_id': str(uuid.uuid4()),
            'generated_at': datetime.now().isoformat(),
            'chain_info': asdict(self.current_chain) if self.current_chain else None,
            'integrity_verification': integrity_check,
            'snapshot_count': len(results),
            'date_range': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None
            },
            'snapshots': []
        }
        
        for result in results:
            snapshot_summary = {
                'snapshot_id': result[0],
                'session_id': result[1],
                'timestamp': result[2],
                'current_hash': result[4],
                'traceability_tag': result[8],
                'compliance_tags': json.loads(result[9]).get('compliance_tags', []),
                'engine_count': len(json.loads(result[6]))
            }
            report['snapshots'].append(snapshot_summary)
        
        return report
    
    def get_chain_statistics(self) -> Dict[str, Any]:
        """Get audit chain statistics"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        # Get basic counts
        cursor.execute('SELECT COUNT(*) FROM forensic_snapshots')
        total_snapshots = cursor.fetchone()[0]
        
        # Get date range
        cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM forensic_snapshots')
        date_range = cursor.fetchone()
        
        # Get compliance tag distribution
        cursor.execute('SELECT compliance_metadata FROM forensic_snapshots')
        compliance_data = cursor.fetchall()
        
        conn.close()
        
        # Process compliance tags
        tag_counts = {}
        for row in compliance_data:
            metadata = json.loads(row[0])
            tags = metadata.get('compliance_tags', [])
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return {
            'chain_id': self.current_chain.chain_id if self.current_chain else None,
            'total_snapshots': total_snapshots,
            'date_range': {
                'earliest': date_range[0],
                'latest': date_range[1]
            },
            'compliance_tag_distribution': tag_counts,
            'storage_path': self.storage_path,
            'integrity_status': 'verified' if self.verify_chain_integrity()['is_valid'] else 'compromised'
        }
