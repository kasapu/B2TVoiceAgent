# Insights & Analytics - Implementation Guide

## Overview
The Insights system provides comprehensive analytics, monitoring, and business intelligence for conversational AI platforms.

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                  Insights & Analytics                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────────────────────────────────────┐          │
│  │         Data Collection Layer               │          │
│  │  • Conversation Logs                        │          │
│  │  • Performance Metrics                      │          │
│  │  • User Actions                             │          │
│  │  • System Events                            │          │
│  └─────────────┬───────────────────────────────┘          │
│                │                                            │
│  ┌─────────────▼───────────────────────────────┐          │
│  │         Data Processing Pipeline            │          │
│  │  • Real-time Stream Processing              │          │
│  │  • Batch Analytics                          │          │
│  │  • Aggregations                             │          │
│  │  • ML-based Insights                        │          │
│  └─────────────┬───────────────────────────────┘          │
│                │                                            │
│  ┌─────────────▼───────────────────────────────┐          │
│  │         Storage Layer                       │          │
│  │  • Time-series DB (InfluxDB)                │          │
│  │  • Document Store (MongoDB)                 │          │
│  │  • Data Warehouse (Snowflake/BigQuery)      │          │
│  └─────────────┬───────────────────────────────┘          │
│                │                                            │
│  ┌─────────────▼───────────────────────────────┐          │
│  │         Analytics Engine                    │          │
│  │  • Conversation Analytics                   │          │
│  │  • NLU Performance                          │          │
│  │  • User Behavior Analysis                   │          │
│  │  • Business Metrics                         │          │
│  │  • Anomaly Detection                        │          │
│  └─────────────┬───────────────────────────────┘          │
│                │                                            │
│  ┌─────────────▼───────────────────────────────┐          │
│  │         Visualization Layer                 │          │
│  │  • Real-time Dashboards                     │          │
│  │  • Custom Reports                           │          │
│  │  • Alerts & Notifications                   │          │
│  └─────────────────────────────────────────────┘          │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Event Tracking System

```python
# models/analytics_event.py
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class EventType(str, Enum):
    """Types of analytics events"""
    CONVERSATION_START = "conversation_start"
    CONVERSATION_END = "conversation_end"
    USER_MESSAGE = "user_message"
    BOT_RESPONSE = "bot_response"
    INTENT_CLASSIFIED = "intent_classified"
    ENTITY_EXTRACTED = "entity_extracted"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    API_CALL = "api_call"
    ERROR = "error"
    USER_FEEDBACK = "user_feedback"
    CUSTOM = "custom"

class AnalyticsEvent(BaseModel):
    """Analytics event model"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Context
    session_id: str
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    
    # Event data
    data: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    channel: Optional[str] = None  # web, mobile, voice
    platform: Optional[str] = None  # ios, android, web
    location: Optional[str] = None
    
    # Performance
    duration_ms: Optional[int] = None
    response_time_ms: Optional[int] = None
    
    # Quality metrics
    confidence: Optional[float] = None
    sentiment: Optional[str] = None
    
    class Config:
        use_enum_values = True

# services/analytics/event_tracker.py
import asyncio
from typing import List
import uuid

class EventTracker:
    """Track and emit analytics events"""
    
    def __init__(self, event_store, stream_processor):
        self.event_store = event_store
        self.stream_processor = stream_processor
        self.buffer = []
        self.buffer_size = 100
        self._flush_task = None
    
    async def track(self, event: AnalyticsEvent):
        """Track an analytics event"""
        # Add to buffer
        self.buffer.append(event)
        
        # Process in real-time stream
        await self.stream_processor.process(event)
        
        # Flush if buffer full
        if len(self.buffer) >= self.buffer_size:
            await self.flush()
    
    async def flush(self):
        """Flush buffered events to storage"""
        if not self.buffer:
            return
        
        events_to_flush = self.buffer.copy()
        self.buffer.clear()
        
        # Batch write to storage
        await self.event_store.batch_insert(events_to_flush)
    
    async def start_auto_flush(self, interval: int = 60):
        """Start automatic flush every N seconds"""
        async def auto_flush():
            while True:
                await asyncio.sleep(interval)
                await self.flush()
        
        self._flush_task = asyncio.create_task(auto_flush())
    
    def stop_auto_flush(self):
        """Stop automatic flush"""
        if self._flush_task:
            self._flush_task.cancel()

# Conversation Analytics
class ConversationAnalytics:
    """Analyze conversation patterns"""
    
    def __init__(self, event_store):
        self.event_store = event_store
    
    async def get_conversation_metrics(
        self,
        agent_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get conversation metrics for date range"""
        events = await self.event_store.query(
            agent_id=agent_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Calculate metrics
        total_conversations = self._count_unique_sessions(events)
        avg_conversation_length = self._calculate_avg_length(events)
        completion_rate = self._calculate_completion_rate(events)
        avg_response_time = self._calculate_avg_response_time(events)
        
        return {
            'total_conversations': total_conversations,
            'avg_conversation_length': avg_conversation_length,
            'completion_rate': completion_rate,
            'avg_response_time_ms': avg_response_time,
            'total_messages': len(events)
        }
    
    def _count_unique_sessions(self, events: List[AnalyticsEvent]) -> int:
        """Count unique conversation sessions"""
        sessions = set(e.session_id for e in events)
        return len(sessions)
    
    def _calculate_avg_length(self, events: List[AnalyticsEvent]) -> float:
        """Calculate average conversation length in turns"""
        from collections import defaultdict
        
        session_lengths = defaultdict(int)
        for event in events:
            if event.event_type in [EventType.USER_MESSAGE, EventType.BOT_RESPONSE]:
                session_lengths[event.session_id] += 1
        
        if not session_lengths:
            return 0
        
        return sum(session_lengths.values()) / len(session_lengths)
    
    def _calculate_completion_rate(self, events: List[AnalyticsEvent]) -> float:
        """Calculate workflow completion rate"""
        started = sum(1 for e in events if e.event_type == EventType.WORKFLOW_STARTED)
        completed = sum(1 for e in events if e.event_type == EventType.WORKFLOW_COMPLETED)
        
        if started == 0:
            return 0
        
        return (completed / started) * 100
    
    def _calculate_avg_response_time(self, events: List[AnalyticsEvent]) -> float:
        """Calculate average bot response time"""
        response_times = [
            e.response_time_ms
            for e in events
            if e.event_type == EventType.BOT_RESPONSE and e.response_time_ms
        ]
        
        if not response_times:
            return 0
        
        return sum(response_times) / len(response_times)

# NLU Performance Analytics
class NLUAnalytics:
    """Analyze NLU performance"""
    
    def __init__(self, event_store):
        self.event_store = event_store
    
    async def get_intent_metrics(
        self,
        agent_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get intent classification metrics"""
        events = await self.event_store.query(
            agent_id=agent_id,
            event_type=EventType.INTENT_CLASSIFIED,
            start_date=start_date,
            end_date=end_date
        )
        
        # Intent distribution
        intent_counts = self._count_intents(events)
        
        # Confidence analysis
        avg_confidence = self._calculate_avg_confidence(events)
        low_confidence_rate = self._calculate_low_confidence_rate(events)
        
        # Fallback rate
        fallback_rate = self._calculate_fallback_rate(intent_counts)
        
        return {
            'intent_distribution': intent_counts,
            'avg_confidence': avg_confidence,
            'low_confidence_rate': low_confidence_rate,
            'fallback_rate': fallback_rate,
            'total_classifications': len(events)
        }
    
    def _count_intents(self, events: List[AnalyticsEvent]) -> Dict[str, int]:
        """Count occurrences of each intent"""
        from collections import Counter
        
        intents = [e.data.get('intent') for e in events if e.data.get('intent')]
        return dict(Counter(intents))
    
    def _calculate_avg_confidence(self, events: List[AnalyticsEvent]) -> float:
        """Calculate average confidence score"""
        confidences = [e.confidence for e in events if e.confidence]
        
        if not confidences:
            return 0
        
        return sum(confidences) / len(confidences)
    
    def _calculate_low_confidence_rate(
        self,
        events: List[AnalyticsEvent],
        threshold: float = 0.7
    ) -> float:
        """Calculate rate of low confidence classifications"""
        total = len(events)
        low_confidence = sum(
            1 for e in events
            if e.confidence and e.confidence < threshold
        )
        
        if total == 0:
            return 0
        
        return (low_confidence / total) * 100
    
    def _calculate_fallback_rate(self, intent_counts: Dict[str, int]) -> float:
        """Calculate fallback intent rate"""
        total = sum(intent_counts.values())
        fallback = intent_counts.get('fallback', 0)
        
        if total == 0:
            return 0
        
        return (fallback / total) * 100

# User Behavior Analytics
class UserBehaviorAnalytics:
    """Analyze user behavior patterns"""
    
    def __init__(self, event_store):
        self.event_store = event_store
    
    async def get_user_journey(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """Get complete user journey for a session"""
        events = await self.event_store.query(
            session_id=session_id
        )
        
        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)
        
        # Build journey
        journey = []
        for event in events:
            journey.append({
                'timestamp': event.timestamp.isoformat(),
                'type': event.event_type,
                'data': event.data
            })
        
        return journey
    
    async def get_drop_off_analysis(
        self,
        agent_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Analyze where users drop off in conversations"""
        events = await self.event_store.query(
            agent_id=agent_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Group by session
        from collections import defaultdict
        sessions = defaultdict(list)
        
        for event in events:
            sessions[event.session_id].append(event)
        
        # Analyze drop-offs
        drop_off_points = defaultdict(int)
        
        for session_id, session_events in sessions.items():
            # Check if session ended naturally
            has_end = any(
                e.event_type == EventType.CONVERSATION_END
                for e in session_events
            )
            
            if not has_end:
                # Find last intent/workflow
                last_event = session_events[-1]
                drop_off_point = last_event.data.get('intent', 'unknown')
                drop_off_points[drop_off_point] += 1
        
        return {
            'drop_off_points': dict(drop_off_points),
            'total_incomplete_sessions': sum(drop_off_points.values())
        }

# Business Metrics
class BusinessMetrics:
    """Calculate business KPIs"""
    
    def __init__(self, event_store):
        self.event_store = event_store
    
    async def get_automation_rate(
        self,
        agent_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate automation rate (% of conversations completed without human)"""
        events = await self.event_store.query(
            agent_id=agent_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Group by session
        from collections import defaultdict
        sessions = defaultdict(list)
        
        for event in events:
            sessions[event.session_id].append(event)
        
        # Count automated vs escalated
        automated = 0
        total = len(sessions)
        
        for session_events in sessions.values():
            # Check if escalated to human
            escalated = any(
                e.data.get('escalated_to_human', False)
                for e in session_events
            )
            
            if not escalated:
                automated += 1
        
        if total == 0:
            return 0
        
        return (automated / total) * 100
    
    async def get_cost_savings(
        self,
        agent_id: str,
        start_date: datetime,
        end_date: datetime,
        cost_per_human_interaction: float = 5.0
    ) -> Dict[str, Any]:
        """Calculate cost savings from automation"""
        automation_rate = await self.get_automation_rate(
            agent_id,
            start_date,
            end_date
        )
        
        # Get total conversations
        events = await self.event_store.query(
            agent_id=agent_id,
            event_type=EventType.CONVERSATION_START,
            start_date=start_date,
            end_date=end_date
        )
        
        total_conversations = len(events)
        automated_conversations = int(
            total_conversations * (automation_rate / 100)
        )
        cost_savings = automated_conversations * cost_per_human_interaction
        
        return {
            'total_conversations': total_conversations,
            'automated_conversations': automated_conversations,
            'automation_rate': automation_rate,
            'cost_savings': cost_savings,
            'cost_per_interaction': cost_per_human_interaction
        }
```

### 2. Real-time Dashboard API

```python
# api/routes/analytics.py
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import datetime, timedelta
from services.analytics.conversation_analytics import ConversationAnalytics
from services.analytics.nlu_analytics import NLUAnalytics
from services.analytics.user_behavior_analytics import UserBehaviorAnalytics
from services.analytics.business_metrics import BusinessMetrics

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

@router.get("/conversations/metrics")
async def get_conversation_metrics(
    agent_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    analytics: ConversationAnalytics = Depends()
):
    """Get conversation metrics"""
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    metrics = await analytics.get_conversation_metrics(
        agent_id=agent_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return metrics

@router.get("/nlu/metrics")
async def get_nlu_metrics(
    agent_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    analytics: NLUAnalytics = Depends()
):
    """Get NLU performance metrics"""
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    metrics = await analytics.get_intent_metrics(
        agent_id=agent_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return metrics

@router.get("/users/journey/{session_id}")
async def get_user_journey(
    session_id: str,
    analytics: UserBehaviorAnalytics = Depends()
):
    """Get user journey for a session"""
    journey = await analytics.get_user_journey(session_id)
    return {"session_id": session_id, "journey": journey}

@router.get("/users/drop-off")
async def get_drop_off_analysis(
    agent_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    analytics: UserBehaviorAnalytics = Depends()
):
    """Get drop-off analysis"""
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    analysis = await analytics.get_drop_off_analysis(
        agent_id=agent_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return analysis

@router.get("/business/automation-rate")
async def get_automation_rate(
    agent_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    metrics: BusinessMetrics = Depends()
):
    """Get automation rate"""
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    rate = await metrics.get_automation_rate(
        agent_id=agent_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return {"automation_rate": rate}

@router.get("/business/cost-savings")
async def get_cost_savings(
    agent_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    cost_per_interaction: float = Query(5.0, description="Cost per human interaction"),
    metrics: BusinessMetrics = Depends()
):
    """Calculate cost savings"""
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    savings = await metrics.get_cost_savings(
        agent_id=agent_id,
        start_date=start_date,
        end_date=end_date,
        cost_per_human_interaction=cost_per_interaction
    )
    
    return savings

@router.get("/dashboard/overview")
async def get_dashboard_overview(
    agent_id: str,
    timeframe: str = Query("30d", regex="^(24h|7d|30d|90d)$")
):
    """Get complete dashboard overview"""
    # Calculate date range
    now = datetime.utcnow()
    if timeframe == "24h":
        start_date = now - timedelta(days=1)
    elif timeframe == "7d":
        start_date = now - timedelta(days=7)
    elif timeframe == "30d":
        start_date = now - timedelta(days=30)
    else:
        start_date = now - timedelta(days=90)
    
    # Gather all metrics
    conv_metrics = await ConversationAnalytics(event_store).get_conversation_metrics(
        agent_id, start_date, now
    )
    
    nlu_metrics = await NLUAnalytics(event_store).get_intent_metrics(
        agent_id, start_date, now
    )
    
    automation_rate = await BusinessMetrics(event_store).get_automation_rate(
        agent_id, start_date, now
    )
    
    return {
        'timeframe': timeframe,
        'conversation_metrics': conv_metrics,
        'nlu_metrics': nlu_metrics,
        'automation_rate': automation_rate
    }
```

### 3. Dashboard UI Components

```typescript
// components/Analytics/MetricsCard.tsx
import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';
import { TrendingUp, TrendingDown } from '@mui/icons-material';

export const MetricsCard: React.FC<{
  title: string;
  value: string | number;
  change?: number;
  icon?: React.ReactNode;
}> = ({ title, value, change, icon }) => {
  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <div>
            <Typography color="text.secondary" gutterBottom>
              {title}
            </Typography>
            <Typography variant="h4">
              {value}
            </Typography>
            {change !== undefined && (
              <Box display="flex" alignItems="center" mt={1}>
                {change > 0 ? (
                  <TrendingUp color="success" fontSize="small" />
                ) : (
                  <TrendingDown color="error" fontSize="small" />
                )}
                <Typography
                  variant="body2"
                  color={change > 0 ? 'success.main' : 'error.main'}
                  ml={0.5}
                >
                  {Math.abs(change)}%
                </Typography>
              </Box>
            )}
          </div>
          {icon && <div>{icon}</div>}
        </Box>
      </CardContent>
    </Card>
  );
};

// components/Analytics/ConversationChart.tsx
import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import { Paper, Typography } from '@mui/material';

export const ConversationChart: React.FC<{
  data: Array<{ date: string; conversations: number }>;
}> = ({ data }) => {
  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Conversation Trend
      </Typography>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="conversations"
            stroke="#8884d8"
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </Paper>
  );
};

// components/Analytics/IntentDistribution.tsx
import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { Paper, Typography } from '@mui/material';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

export const IntentDistribution: React.FC<{
  data: { [intent: string]: number };
}> = ({ data }) => {
  const chartData = Object.entries(data).map(([name, value]) => ({
    name,
    value
  }));

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Intent Distribution
      </Typography>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) =>
              `${name} ${(percent * 100).toFixed(0)}%`
            }
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </Paper>
  );
};
```

This comprehensive Insights & Analytics system provides real-time monitoring, business intelligence, and actionable insights for your B2T Voice platform.

Now let me package everything together with a deployment guide:
