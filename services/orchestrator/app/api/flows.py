"""
Dialogue flow management endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, text
from typing import List, Optional
import uuid
import logging

from app.core.database import get_db
from app.models.schemas import DialogueFlowCreate, DialogueFlow, FlowPublishRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=List[DialogueFlow])
async def list_flows(
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    List all dialogue flows

    Optionally filter by active status
    """
    try:
        query_str = "SELECT * FROM dialogue_flows"
        if is_active is not None:
            query_str += f" WHERE is_active = {is_active}"
        query_str += " ORDER BY created_at DESC"

        result = await db.execute(text(query_str))
        flows = result.fetchall()

        return [
            DialogueFlow(
                flow_id=row[0],
                flow_name=row[1],
                version=row[4],
                is_active=row[5],
                flow_definition=row[3],
                created_at=row[8],
                updated_at=row[9]
            )
            for row in flows
        ]

    except Exception as e:
        logger.error(f"Failed to list flows: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list flows: {str(e)}")


@router.get("/{flow_id}", response_model=DialogueFlow)
async def get_flow(
    flow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific dialogue flow by ID"""
    try:
        result = await db.execute(
            text("SELECT * FROM dialogue_flows WHERE flow_id = :flow_id"),
            {"flow_id": flow_id}
        )
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Flow not found")

        return DialogueFlow(
            flow_id=row[0],
            flow_name=row[1],
            version=row[4],
            is_active=row[5],
            flow_definition=row[3],
            created_at=row[8],
            updated_at=row[9]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get flow: {str(e)}")


@router.post("", response_model=DialogueFlow, status_code=201)
async def create_flow(
    request: DialogueFlowCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new dialogue flow

    Flow definition should be a JSON object with nodes and edges
    """
    try:
        # Check if flow name already exists
        result = await db.execute(
            text("SELECT flow_id FROM dialogue_flows WHERE flow_name = :flow_name"),
            {"flow_name": request.flow_name}
        )
        if result.fetchone():
            raise HTTPException(status_code=409, detail="Flow name already exists")

        # Insert new flow
        flow_id = uuid.uuid4()
        await db.execute(
            text("""
            INSERT INTO dialogue_flows (
                flow_id, flow_name, description, flow_definition,
                version, is_active, traffic_percentage
            ) VALUES (
                :flow_id, :flow_name, :description, :flow_definition,
                1, FALSE, :traffic_percentage
            )
            """),
            {
                "flow_id": flow_id,
                "flow_name": request.flow_name,
                "description": request.description,
                "flow_definition": request.flow_definition,
                "traffic_percentage": request.traffic_percentage
            }
        )
        await db.commit()

        logger.info(f"Created flow {flow_id}: {request.flow_name}")

        # Fetch and return created flow
        result = await db.execute(
            text("SELECT * FROM dialogue_flows WHERE flow_id = :flow_id"),
            {"flow_id": flow_id}
        )
        row = result.fetchone()

        return DialogueFlow(
            flow_id=row[0],
            flow_name=row[1],
            version=row[4],
            is_active=row[5],
            flow_definition=row[3],
            created_at=row[8],
            updated_at=row[9]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create flow: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create flow: {str(e)}")


@router.post("/{flow_id}/publish")
async def publish_flow(
    flow_id: uuid.UUID,
    request: FlowPublishRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Publish a flow version (make it active)

    Optionally set traffic percentage for A/B testing
    """
    try:
        # Check if flow exists
        result = await db.execute(
            text("SELECT flow_id FROM dialogue_flows WHERE flow_id = :flow_id"),
            {"flow_id": flow_id}
        )
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Flow not found")

        # Update flow
        await db.execute(
            text("""
            UPDATE dialogue_flows
            SET is_active = TRUE,
                published_at = NOW(),
                traffic_percentage = :traffic_percentage
            WHERE flow_id = :flow_id
            """),
            {
                "flow_id": flow_id,
                "traffic_percentage": request.traffic_percentage
            }
        )
        await db.commit()

        logger.info(f"Published flow {flow_id} with {request.traffic_percentage}% traffic")

        return {
            "flow_id": flow_id,
            "status": "published",
            "traffic_percentage": request.traffic_percentage
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to publish flow {flow_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to publish flow: {str(e)}")
