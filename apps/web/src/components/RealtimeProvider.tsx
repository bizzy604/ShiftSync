import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../auth/AuthContext';
import { keys } from '../lib/api/hooks';

interface RealtimeContextType {
    isConnected: boolean;
    lastEvent: string | null;
}

const RealtimeContext = createContext<RealtimeContextType>({
    isConnected: false,
    lastEvent: null,
});

export const useRealtime = () => useContext(RealtimeContext);

export function RealtimeProvider({ children }: { children: React.ReactNode }) {
    const { user } = useAuth();
    const queryClient = useQueryClient();
    const [isConnected, setIsConnected] = useState(false);
    const [lastEvent, setLastEvent] = useState<string | null>(null);
    const socketRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<number | null>(null);

    useEffect(() => {
        if (!user) {
            if (socketRef.current) {
                socketRef.current.close();
            }
            return;
        }

        const connect = () => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            // Use window.location.hostname:8000 to ensure we match the backend port and have consistent cookies
            const backendHost = `${window.location.hostname}:8000`;

            const wsUrl = `${protocol}//${backendHost}/api/v1/realtime/ws`;

            console.log(`[Realtime] Connecting to ${wsUrl}...`);
            const socket = new WebSocket(wsUrl);
            socketRef.current = socket;

            socket.onopen = () => {
                console.log('[Realtime] Connected');
                setIsConnected(true);
                if (reconnectTimeoutRef.current) {
                    window.clearTimeout(reconnectTimeoutRef.current);
                    reconnectTimeoutRef.current = null;
                }
            };

            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    const { event: eventName, payload } = data;

                    console.log(`[Realtime] Received event: ${eventName}`, payload);
                    setLastEvent(eventName);

                    const invalidateScheduleData = () => {
                        queryClient.invalidateQueries({ queryKey: ['shifts'] });
                        queryClient.invalidateQueries({ queryKey: ['assignments'] });
                        queryClient.invalidateQueries({ queryKey: keys.myAssignments });
                        queryClient.invalidateQueries({ queryKey: ['analytics', 'onDuty'] });
                    };

                    // Handle specific events
                    if (eventName === 'notification.new') {
                        queryClient.invalidateQueries({ queryKey: ['notifications'] });
                        if (typeof payload?.type === 'string' && payload.type.startsWith('drop.')) {
                            queryClient.invalidateQueries({ queryKey: keys.drops });
                        }
                    } else if (eventName === 'swap.status_changed') {
                        queryClient.invalidateQueries({ queryKey: keys.swaps });
                        queryClient.invalidateQueries({ queryKey: keys.drops });
                        queryClient.invalidateQueries({ queryKey: keys.myAssignments });
                        if (payload.swapRequestId) {
                            queryClient.invalidateQueries({ queryKey: keys.swap(payload.swapRequestId) });
                        }
                    } else if (eventName === 'schedule.published' || eventName === 'schedule.updated') {
                        invalidateScheduleData();
                    } else if (eventName === 'assignment.changed') {
                        invalidateScheduleData();
                    } else if (eventName === 'assignment.conflict') {
                        queryClient.invalidateQueries({ queryKey: ['assignments'] });
                    }
                } catch (err) {
                    console.error('[Realtime] Error parsing message', err);
                }
            };

            socket.onclose = (event) => {
                console.log(`[Realtime] Disconnected: ${event.reason} (${event.code})`);
                setIsConnected(false);
                socketRef.current = null;

                // Simple exponential backoff for reconnection
                if (user) {
                    console.log('[Realtime] Attempting reconnect in 5s...');
                    reconnectTimeoutRef.current = window.setTimeout(connect, 5000);
                }
            };

            socket.onerror = (err) => {
                console.error('[Realtime] WebSocket error', err);
                socket.close();
            };
        };

        connect();

        return () => {
            if (socketRef.current) {
                socketRef.current.close();
            }
            if (reconnectTimeoutRef.current) {
                window.clearTimeout(reconnectTimeoutRef.current);
            }
        };
    }, [user, queryClient]);

    return (
        <RealtimeContext.Provider value={{ isConnected, lastEvent }}>
            {children}
        </RealtimeContext.Provider>
    );
}
