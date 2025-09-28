import React, { useEffect, useMemo, useRef, useState } from "react";
import { getBackendBaseUrl, joinUrl } from "../utils/backendUrls";

const SNAPSHOT_INTERVAL_MS = 800;
const STALE_THRESHOLD_MS = 6000;
const STALE_CHECK_MS = 2000;
const SNAPSHOT_BACKOFF_MAX_MS = 8000;
const SNAPSHOT_BACKOFF_GROWTH = 1.6;
const SNAPSHOT_FRAME_MIN_BYTES = 130;

export default function LiveVideo({ config }) {
  const backendBase = useMemo(
    () => getBackendBaseUrl(config?.backendBase),
    [config?.backendBase]
  );

  const mjpegPrimaryUrl = useMemo(
    () => joinUrl(backendBase, "api/video_feed"),
    [backendBase]
  );
  const mjpegFallbackUrl = useMemo(
    () => joinUrl(backendBase, "api/video_feed_force_fallback"),
    [backendBase]
  );
  const snapshotUrl = useMemo(
    () => joinUrl(backendBase, "api/frame/latest"),
    [backendBase]
  );
  const detectMetricsUrl = useMemo(
    () => joinUrl(backendBase, "api/detect/metrics"),
    [backendBase]
  );

  const forceFallback = config?.forceFallback ||
    (typeof window !== "undefined" && window.__SAFEFALL_FORCE_FALLBACK__ === true);
  const debug = typeof window !== "undefined" && window.location.search.includes("debugStream=1");
  const detectDebug = typeof window !== "undefined" && window.location.search.includes("debugDetect=1");

  const imgRef = useRef(null);
  const abortRef = useRef(null);
  const backoffRef = useRef(800);

  const [mode, setMode] = useState(forceFallback ? "fallback" : "mjpeg");
  const [tick, setTick] = useState(() => Date.now());
  const [errorType, setErrorType] = useState(null);
  const [retry, setRetry] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [lastFrameTs, setLastFrameTs] = useState(null);

  const mjpegSrc = useMemo(() => {
    if (mode === "mjpeg") {
      return `${mjpegPrimaryUrl}?_=${tick}`;
    }
    if (mode === "fallback") {
      return `${mjpegFallbackUrl}?_=${tick}`;
    }
    return "";
  }, [mode, tick, mjpegPrimaryUrl, mjpegFallbackUrl]);

  useEffect(() => {
    setMode(forceFallback ? "fallback" : "mjpeg");
    setIsLoading(true);
  }, [forceFallback, backendBase]);

  useEffect(() => {
    if (mode !== "snapshot") {
      return undefined;
    }

    let cancelled = false;

    const pullSnapshot = async () => {
      try {
        const response = await fetch(snapshotUrl, { cache: "no-store" });
        if (!response.ok) {
          return;
        }
        const blob = await response.blob();
        if (blob.size > SNAPSHOT_FRAME_MIN_BYTES) {
          setLastFrameTs(Date.now());
        }
        const nextUrl = URL.createObjectURL(blob);
        if (imgRef.current && !cancelled) {
          imgRef.current.onload = () => URL.revokeObjectURL(nextUrl);
          imgRef.current.src = nextUrl;
        }
        if (!cancelled) {
          setIsLoading(false);
        }
      } catch (error) {
        if (debug && !cancelled) {
          console.warn("[LiveVideo] snapshot fetch failed", error);
        }
      }
    };

    const timer = setInterval(pullSnapshot, SNAPSHOT_INTERVAL_MS);
    pullSnapshot();

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [mode, snapshotUrl, debug]);

  useEffect(() => {
    if (mode === "snapshot") {
      return undefined;
    }

    const timer = setInterval(() => {
      if (!imgRef.current || !lastFrameTs) {
        return;
      }
      if (Date.now() - lastFrameTs > STALE_THRESHOLD_MS) {
        if (debug) {
          console.warn("[LiveVideo] stream stale, switching to snapshot");
        }
        setMode("snapshot");
      }
    }, STALE_CHECK_MS);

    return () => clearInterval(timer);
  }, [mode, lastFrameTs, debug]);

  const preflightCheck = async (url) => {
    try {
      const controller = new AbortController();
      abortRef.current = controller;
      const response = await fetch(url, {
        method: "GET",
        signal: controller.signal,
        cache: "no-store",
      });
      return response.ok;
    } catch (error) {
      return false;
    }
  };

  useEffect(() => {
    if (forceFallback && mode === "fallback") {
      return undefined;
    }
    if (mode !== "mjpeg" && mode !== "fallback") {
      return undefined;
    }

    let cancelled = false;
    const target = mode === "mjpeg" ? mjpegPrimaryUrl : mjpegFallbackUrl;

    (async () => {
      const ok = await preflightCheck(`${target}?preflight=${Date.now()}`);
      if (cancelled) {
        return;
      }
      if (!ok) {
        if (mode === "mjpeg") {
          setMode("fallback");
          setIsLoading(true);
          setErrorType("refused");
          setTick(Date.now());
        } else {
          setMode("snapshot");
          setIsLoading(true);
          setErrorType("refused");
        }
      } else {
        setTick(Date.now());
        setErrorType(null);
      }
    })();

    return () => {
      cancelled = true;
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, mjpegPrimaryUrl, mjpegFallbackUrl, forceFallback]);

  const handleLoad = () => {
    try {
      if (
        imgRef.current &&
        (imgRef.current.naturalWidth <= 2 || imgRef.current.naturalHeight <= 2)
      ) {
        if (debug) {
          console.log("[LiveVideo] placeholder frame ignored");
        }
        setTimeout(() => setTick(Date.now()), 400);
        return;
      }
    } catch (error) {
      if (debug) {
        console.warn("[LiveVideo] load check error", error);
      }
    }

    setLastFrameTs(Date.now());
    setIsLoading(false);
    setErrorType(null);
    if (debug) {
      console.log("[LiveVideo] frame loaded", mode, backendBase);
    }
    backoffRef.current = 800;
  };

  const handleError = () => {
    if (debug) {
      console.warn("[LiveVideo] load error", mode, "retry", retry);
    }

    setIsLoading(true);
    setRetry((prev) => prev + 1);

    if (mode === "mjpeg") {
      setErrorType("refused");
      setMode("fallback");
      setTick(Date.now());
      return;
    }

    if (mode === "fallback") {
      setErrorType("refused");
      setMode("snapshot");
      return;
    }

    setTimeout(() => setTick(Date.now()), backoffRef.current);
    backoffRef.current = Math.min(
      backoffRef.current * SNAPSHOT_BACKOFF_GROWTH,
      SNAPSHOT_BACKOFF_MAX_MS
    );
  };

  const renderOverlay = () => {
    if (!isLoading && !errorType) {
      return null;
    }
    if (mode === "snapshot" && !isLoading && !errorType) {
      return null;
    }

    let message = "Loading stream...";
    if (errorType === "refused") {
      message = mode === "snapshot"
        ? "Stream offline - showing snapshots"
        : "Primary stream refused - trying fallback";
    } else if (mode === "fallback") {
      message = "Fallback stream in progress...";
    }

    return (
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          zIndex: 2,
          color: errorType ? "#ff6666" : "#666",
          fontSize: 14,
          textAlign: "center",
          whiteSpace: "pre-line",
        }}
      >
        {message}
        <div style={{ marginTop: 6, fontSize: 11, opacity: 0.8 }}>
          {backendBase}
        </div>
      </div>
    );
  };

  useEffect(() => {
    if (!detectDebug) {
      return undefined;
    }
    const id = setInterval(async () => {
      try {
        const payload = await fetch(detectMetricsUrl, { cache: "no-store" }).then((r) => r.json());
        console.log("[DetectMetrics]", payload);
      } catch (error) {
        console.warn("[DetectMetrics] error", error);
      }
    }, 5000);
    return () => clearInterval(id);
  }, [detectDebug, detectMetricsUrl]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      {renderOverlay()}
      {mode !== "snapshot" && (
        <img
          ref={imgRef}
          src={mjpegSrc}
          alt="Live Stream"
          onLoad={handleLoad}
          onError={handleError}
          style={{
            display: "block",
            width: "100%",
            height: "auto",
            borderRadius: 8,
            background: "#000",
            opacity: isLoading ? 0.55 : 1,
            transition: "opacity .25s",
          }}
        />
      )}
      {mode === "snapshot" && (
        <img
          ref={imgRef}
          alt="Live Snapshot"
          style={{
            display: "block",
            width: "100%",
            height: "auto",
            borderRadius: 8,
            background: "#000",
            opacity: isLoading ? 0.55 : 1,
            transition: "opacity .25s",
          }}
        />
      )}
      {debug && (
        <div
          style={{
            position: "absolute",
            left: 8,
            bottom: 8,
            background: "rgba(0,0,0,0.55)",
            color: "#0f0",
            fontSize: 10,
            padding: "4px 6px",
            borderRadius: 4,
            lineHeight: 1.3,
          }}
        >
          <div>mode: {mode}</div>
          <div>forceFallback: {String(forceFallback)}</div>
          <div>retry: {retry}</div>
          <div>last: {lastFrameTs ? ((Date.now() - lastFrameTs) / 1000).toFixed(1) + "s" : "-"}</div>
          <div>err: {errorType || "none"}</div>
          <div>base: {backendBase}</div>
        </div>
      )}
    </div>
  );
}
