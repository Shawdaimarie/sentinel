package aegis

import (
	"sync"
	"time"
)

type RateLimitSpec struct {
	Limit         int `json:"limit"`
	WindowSeconds int `json:"window_seconds"`
}

type rateBucket struct {
	Count   int
	ResetAt time.Time
}

type RateLimiter struct {
	mu      sync.Mutex
	buckets map[string]rateBucket
}

func NewRateLimiter() *RateLimiter {
	return &RateLimiter{buckets: make(map[string]rateBucket)}
}

func (r *RateLimiter) Allow(key string, spec RateLimitSpec, now time.Time) bool {
	if spec.Limit <= 0 || spec.WindowSeconds <= 0 {
		return true
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	bucket := r.buckets[key]
	if bucket.ResetAt.IsZero() || !now.Before(bucket.ResetAt) {
		bucket = rateBucket{ResetAt: now.Add(time.Duration(spec.WindowSeconds) * time.Second)}
	}
	if bucket.Count >= spec.Limit {
		r.buckets[key] = bucket
		return false
	}
	bucket.Count++
	r.buckets[key] = bucket
	return true
}
