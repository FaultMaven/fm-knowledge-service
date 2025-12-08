"""Initial schema for documents table

Revision ID: 001_initial
Revises:
Create Date: 2025-01-07 00:00:00.000000

NOTE: This migration only manages SQL metadata.
Vector embeddings are stored separately in ChromaDB and are NOT managed by Alembic.
The embedding_id column links SQL documents to ChromaDB vectors.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create documents table for metadata (vectors stored in ChromaDB)."""
    op.create_table(
        'documents',
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('doc_metadata', sa.JSON(), nullable=False),
        sa.Column('embedding_id', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('document_id')
    )

    # Create indexes for performance
    op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'], unique=False)
    op.create_index(op.f('ix_documents_document_type'), 'documents', ['document_type'], unique=False)
    op.create_index(op.f('ix_documents_embedding_id'), 'documents', ['embedding_id'], unique=True)


def downgrade() -> None:
    """Drop documents table."""
    op.drop_index(op.f('ix_documents_embedding_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_document_type'), table_name='documents')
    op.drop_index(op.f('ix_documents_user_id'), table_name='documents')
    op.drop_table('documents')
