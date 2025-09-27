package main

import (
    "flag"
    "fmt"
    "math/big"
    "os"
    "runtime"
    "strings"
    "sync"
    "sync/atomic"
    "time"
)

// string.printable (100 chars)
const DEFAULT_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~ \t\n\r\x0b\x0c"

type Params struct {
    N *big.Int
    E *big.Int
    C *big.Int
}

type Result struct {
    Found bool
    PIN   string
}

// fastModExp65537 computes base^65537 mod n using 16 squarings + final multiply.
// Falls back to Exp for other exponents.
func fastModExp65537(dst, base, e, n *big.Int) *big.Int {
    // e == 65537?
    if e.BitLen() == 17 && e.Bit(16) == 1 && e.Bit(0) == 1 && e.Bit(1) == 0 {
        var t big.Int
        t.Set(base)                    // t = base
        for i := 0; i < 16; i++ {      // t = base^(2^16) mod n
            t.Mul(&t, &t)
            t.Mod(&t, n)
        }
        dst.Mul(&t, base)              // dst = t * base
        dst.Mod(dst, n)
        return dst
    }
    return dst.Exp(base, e, n)
}

func worker(alphabet []byte, pinLen int, p Params, startIdx, step int,
    resultCh chan Result, wg *sync.WaitGroup, stopCh <-chan struct{}, attempts *uint64) {
    defer wg.Done()

    var m big.Int
    var out big.Int

    pin := make([]byte, pinLen)
    L := len(alphabet)
    const flushEvery = 1024
    var local uint64

    for i := startIdx; i < L; i += step { // fixed first char by worker shard
        pin[0] = alphabet[i]
        for i1 := 0; i1 < L; i1++ { pin[1] = alphabet[i1]
        for i2 := 0; i2 < L; i2++ { pin[2] = alphabet[i2]
        for i3 := 0; i3 < L; i3++ { pin[3] = alphabet[i3]
        for i4 := 0; i4 < L; i4++ { pin[4] = alphabet[i4]
        for i5 := 0; i5 < L; i5++ { pin[5] = alphabet[i5]

            select {
            case <-stopCh:
                if local != 0 { atomic.AddUint64(attempts, local) }
                return
            default:
            }

            // m = BigEndian(pin)
            m.SetBytes(pin)
            // out = m^e mod N (optimized for 65537)
            fastModExp65537(&out, &m, p.E, p.N)

            if out.Cmp(p.C) == 0 {
                resultCh <- Result{Found: true, PIN: string(pin)}
                if local != 0 { atomic.AddUint64(attempts, local) }
                return
            }

            local++
            if local == flushEvery {
                atomic.AddUint64(attempts, local)
                local = 0
            }
        }}}}}
    }
    if local != 0 { atomic.AddUint64(attempts, local) }
}

func progress(total uint64, attempts *uint64, start time.Time, stop <-chan struct{}) {
    ticker := time.NewTicker(200 * time.Millisecond)
    defer ticker.Stop()
    spinner := []rune{'|','/','-','\\'}
    s := 0
    for {
        select {
        case <-stop:
            fmt.Fprint(os.Stderr, "\r"+strings.Repeat(" ", 100)+"\r")
            return
        case <-ticker.C:
            tried := atomic.LoadUint64(attempts)
            elapsed := time.Since(start).Seconds()
            rate := float64(tried) / (elapsed + 1e-9)
            frac := float64(tried) / float64(total)
            if frac > 1 { frac = 1 }
            barW := 30
            filled := int(frac * float64(barW))
            bar := strings.Repeat("#", filled) + strings.Repeat("-", barW-filled)
            eta := 0.0
            if rate > 1e-9 { eta = (float64(total) - float64(tried)) / rate }
            fmt.Fprintf(os.Stderr, "\r[%s] %3.0f%% %c tried=%d/%d rate=%.0f/s eta=%.1fs",
                bar, frac*100, spinner[s%4], tried, total, rate, eta)
            s++
        }
    }
}

func main() {
    // Flags
    var nStr, eStr, cStr string
    var pinLen int
    var threads int
    var timeoutSec int
    var alphabet string

    flag.StringVar(&nStr, "n", "", "RSA modulus n (decimal)")
    flag.StringVar(&eStr, "e", "65537", "RSA public exponent e (decimal)")
    flag.StringVar(&cStr, "c", "", "Ciphertext c (decimal)")
    flag.IntVar(&pinLen, "len", 6, "PIN length")
    flag.IntVar(&threads, "threads", runtime.NumCPU(), "Number of goroutines")
    flag.IntVar(&timeoutSec, "timeout", 0, "Timeout seconds (0=no timeout)")
    flag.StringVar(&alphabet, "alphabet", DEFAULT_ALPHABET, "Alphabet to brute-force")
    flag.Parse()

    // Preset defaults if no args given
    if len(os.Args) == 1 {
        nStr = "12797238567939373327290740181067928655036715140086366228695600354441701805042996693724492073962821232105794144227525679428233867878596111656619420618371273"
        eStr = "65537"
        cStr = "3527077117699128297213675720714263452674443031519633052631407312233044869485683860610136570675841069826332336207623212194708283745914346102673061030089974"
        pinLen = 6
        threads = 6
        timeoutSec = 0
    }

    if nStr == "" || cStr == "" {
        fmt.Println("Usage: go run main.go -n <n> -e 65537 -c <c> [-len 6] [-threads N] [-timeout SEC]")
        os.Exit(2)
    }

    p := Params{N: new(big.Int), E: new(big.Int), C: new(big.Int)}
    if _, ok := p.N.SetString(nStr, 10); !ok { fmt.Println("invalid n"); os.Exit(2) }
    if _, ok := p.E.SetString(eStr, 10); !ok { fmt.Println("invalid e"); os.Exit(2) }
    if _, ok := p.C.SetString(cStr, 10); !ok { fmt.Println("invalid c"); os.Exit(2) }

    if threads <= 0 { threads = 1 }
    if pinLen != 6 { fmt.Println("Warning: code assumes 6 for tight inner loops; other lengths will be slower.") }

    fmt.Printf("[INFO] Go brute-force starting with %d threads\n", threads)
    fmt.Printf("[INFO] Alphabet=%d, Len=%d\n", len(alphabet), pinLen)

    // total space (fits in 64-bit for 100^6)
    total := uint64(1)
    for i := 0; i < pinLen; i++ { total *= uint64(len(alphabet)) }
    fmt.Printf("[INFO] Total candidates: %d\n", total)

    var wg sync.WaitGroup
    resultCh := make(chan Result, 1)
    stopAll := make(chan struct{})
    var attempts uint64

    start := time.Now()
    go progress(total, &attempts, start, stopAll)

    // fan out workers by first character shard
    ab := []byte(alphabet)
    for i := 0; i < threads; i++ {
        wg.Add(1)
        go worker(ab, pinLen, p, i, threads, resultCh, &wg, stopAll, &attempts)
    }

    // timeout handling
    var timeoutC <-chan time.Time
    if timeoutSec > 0 { timeoutC = time.After(time.Duration(timeoutSec) * time.Second) }

    var res Result
    select {
    case res = <-resultCh:
        close(stopAll)
    case <-timeoutC:
        fmt.Println("\n[FAILURE] Timeout, not found")
        close(stopAll)
        res = Result{Found: false}
    }

    wg.Wait()
    close(stopAll)
    fmt.Fprint(os.Stderr, "\r"+strings.Repeat(" ", 100)+"\r")

    if res.Found {
        fmt.Printf("[SUCCESS] PIN: %q\n", res.PIN)
        fmt.Printf("[SUCCESS] Elapsed: %s\n", time.Since(start))
    } else {
        fmt.Println("[FAILURE] Not found")
    }
}
