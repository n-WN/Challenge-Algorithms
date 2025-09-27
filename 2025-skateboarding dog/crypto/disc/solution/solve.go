// author: Swizzer

package main

import (
	"flag"
	"fmt"
	"math/big"
	"os"
	"strings"
)

const (
	wordsPath = "words_alpha.txt"
	e         = 65537
)

type trieNode struct {
	child [26]*trieNode
	end   bool
}
type revTrie struct{ root *trieNode }

func newTrie() *revTrie { return &revTrie{root: &trieNode{}} }
func (t *revTrie) insert(w string) {
	if w == "" {
		return
	}
	for i := 0; i < len(w); i++ {
		if w[i] < 'a' || w[i] > 'z' {
			return
		}
	}
	cur := t.root
	for i := len(w) - 1; i >= 0; i-- {
		idx := int(w[i] - 'a')
		if cur.child[idx] == nil {
			cur.child[idx] = &trieNode{}
		}
		cur = cur.child[idx]
	}
	cur.end = true
}
func loadWords(path string) *revTrie {
	b, _ := os.ReadFile(path)
	tr := newTrie()
	for _, w := range strings.Split(string(b), "\n") {
		tr.insert(strings.TrimSpace(w))
	}
	return tr
}

type wstate struct {
	node      *trieNode
	prevSpace bool
}

func startState(tr *revTrie) wstate { return wstate{node: tr.root} }
func (s wstate) letter(b byte) (wstate, bool) {
	if b < 'a' || b > 'z' || s.node == nil {
		return s, false
	}
	nxt := s.node.child[int(b-'a')]
	if nxt == nil {
		return s, false
	}
	return wstate{node: nxt}, true
}
func (s wstate) space(tr *revTrie) (wstate, bool) {
	if s.prevSpace || s.node == nil || !s.node.end {
		return s, false
	}
	return wstate{node: tr.root, prevSpace: true}, true
}
func (s wstate) endWord() bool { return s.node != nil && s.node.end }

func le256(n *big.Int) []int {
	if n.Sign() == 0 {
		return []int{0}
	}
	be := n.Bytes()
	out := make([]int, len(be))
	for i := 0; i < len(be); i++ {
		out[i] = int(be[len(be)-1-i])
	}
	return out
}

var inv256 [256]int

func initInv() {
	for a := 1; a < 256; a += 2 {
		for x := 1; x < 256; x += 2 {
			if (a*x)&255 == 1 {
				inv256[a] = x
				break
			}
		}
	}
}

func parseBig(s string) *big.Int {
	n, ok := new(big.Int).SetString(strings.TrimSpace(s), 10)
	if !ok {
		panic("bad integer")
	}
	return n
}

func solve(n *big.Int, tr *revTrie) (string, string, bool) {
	N := le256(n)
	B := len(N)

	for Lp := 1; Lp < B; Lp++ {
		for _, Lq := range []int{B - Lp, B - Lp + 1} {
			if Lq <= 0 {
				continue
			}
			n0 := N[0]
			var ansP, ansQ []byte
			found := false

			for p0 := byte('a'); p0 <= 'z'; p0++ {
				if found || p0%2 == 0 {
					continue
				}
				p0inv := inv256[p0]
				pst0, okp := startState(tr).letter(p0)
				if !okp || (Lp == 1 && !pst0.endWord()) {
					continue
				}
				for q0 := byte('a'); q0 <= 'z'; q0++ {
					if found || q0%2 == 0 || ((int(q0)*int(p0))&255) != n0 {
						continue
					}
					qst0, okq := startState(tr).letter(q0)
					if !okq || (Lq == 1 && !qst0.endWord()) {
						continue
					}

					p := make([]int, Lp)
					q := make([]int, Lq)
					for i := range p {
						p[i] = -1
					}
					for i := range q {
						q[i] = -1
					}
					p[0] = int(p0)
					q[0] = int(q0)

					var dfs func(i, carry int, ps, qs wstate) bool
					dfs = func(i, carry int, ps, qs wstate) bool {
						if i == B {
							if carry != 0 || !ps.endWord() || !qs.endWord() {
								return false
							}
							pp := make([]byte, Lp)
							qq := make([]byte, Lq)
							for k := 0; k < Lp; k++ {
								if p[k] < 0 {
									return false
								}
								pp[Lp-1-k] = byte(p[k])
							}
							for k := 0; k < Lq; k++ {
								if q[k] < 0 {
									return false
								}
								qq[Lq-1-k] = byte(q[k])
							}
							if pp[0] == ' ' || qq[0] == ' ' {
								return false
							}
							ansP, ansQ, found = pp, qq, true
							return true
						}

						sum := carry
						for j := 1; j < i; j++ {
							if j < Lp && (i-j) < Lq && p[j] >= 0 && q[i-j] >= 0 {
								sum += p[j] * q[i-j]
							}
						}
						ni := N[i]

						if i < Lp {
							// try space for p[i]
							if i > 0 && i < Lp-1 && ps.node != nil && ps.node.end && !ps.prevSpace {
								rhs := ni - sum - (int(' ') * q[0])
								rhs = ((rhs % 256) + 256) % 256
								qim := (p0inv * rhs) & 255
								if i < Lq {
									b := byte(qim)
									if b == ' ' || (b >= 'a' && b <= 'z') {
										if b == ' ' {
											if i != Lq-1 {
												if nqs, ok := qs.space(tr); ok {
													p[i], q[i] = int(' '), qim
													tot := sum + int(' ')*q[0] + p[0]*qim
													if (tot&255) == ni && dfs(i+1, (tot-ni)>>8, wstate{node: tr.root, prevSpace: true}, nqs) {
														return true
													}
													p[i], q[i] = -1, -1
												}
											}
										} else {
											if nqs, ok := qs.letter(b); ok && !(i == Lq-1 && !nqs.endWord()) {
												p[i], q[i] = int(' '), qim
												tot := sum + int(' ')*q[0] + p[0]*qim
												if (tot&255) == ni && dfs(i+1, (tot-ni)>>8, wstate{node: tr.root, prevSpace: true}, nqs) {
													return true
												}
												p[i], q[i] = -1, -1
											}
										}
									}
								} else if qim == 0 {
									p[i] = int(' ')
									tot := sum + int(' ')*q[0]
									if (tot&255) == ni && dfs(i+1, (tot-ni)>>8, wstate{node: tr.root, prevSpace: true}, qs) {
										return true
									}
									p[i] = -1
								}
							}
							// try letters for p[i]
							for ch := byte('a'); ch <= 'z'; ch++ {
								nps, ok := ps.letter(ch)
								if !ok || (i == Lp-1 && !nps.endWord()) {
									continue
								}
								p[i] = int(ch)
								rhs := ni - sum - (int(ch) * q[0])
								rhs = ((rhs % 256) + 256) % 256
								qim := (p0inv * rhs) & 255
								if i < Lq {
									b := byte(qim)
									if b != ' ' && (b < 'a' || b > 'z') {
										p[i] = -1
										continue
									}
									var nqs wstate
									var ok2 bool
									if b == ' ' {
										if i == Lq-1 {
											p[i] = -1
											continue
										}
										nqs, ok2 = qs.space(tr)
									} else {
										nqs, ok2 = qs.letter(b)
										if ok2 && i == Lq-1 && !nqs.endWord() {
											ok2 = false
										}
									}
									if !ok2 {
										p[i] = -1
										continue
									}
									q[i] = qim
									tot := sum + int(ch)*q[0] + p[0]*qim
									if (tot & 255) == ni {
										if dfs(i+1, (tot-ni)>>8, nps, nqs) {
											return true
										}
									}
									p[i], q[i] = -1, -1
								} else {
									if qim != 0 {
										p[i] = -1
										continue
									}
									tot := sum + int(ch)*q[0]
									if (tot & 255) == ni {
										if dfs(i+1, (tot-ni)>>8, nps, qs) {
											return true
										}
									}
									p[i] = -1
								}
							}
						} else {
							// i >= Lp : only q[i]
							rhs := ni - sum
							rhs = ((rhs % 256) + 256) % 256
							qim := (p0inv * rhs) & 255
							if i < Lq {
								b := byte(qim)
								if b == ' ' || (b >= 'a' && b <= 'z') {
									if b == ' ' {
										if i == Lq-1 {
											return false
										}
										if nqs, ok := qs.space(tr); ok {
											q[i] = qim
											tot := sum + p[0]*qim
											if (tot&255) == ni && dfs(i+1, (tot-ni)>>8, ps, nqs) {
												return true
											}
											q[i] = -1
										}
									} else {
										if nqs, ok := qs.letter(b); ok && !(i == Lq-1 && !nqs.endWord()) {
											q[i] = qim
											tot := sum + p[0]*qim
											if (tot&255) == ni && dfs(i+1, (tot-ni)>>8, ps, nqs) {
												return true
											}
											q[i] = -1
										}
									}
								}
							} else {
								if qim != 0 || (sum&255) != ni {
									return false
								}
								return dfs(i+1, (sum-ni)>>8, ps, qs)
							}
						}
						return false
					}

					if dfs(1, (int(p0)*int(q0))>>8, pst0, qst0) {
						return string(ansP), string(ansQ), true
					}
				}
			}
		}
	}
	return "", "", false
}

func main() {
	nStr := flag.String("n", "", "modulus n (decimal)")
	cStr := flag.String("c", "", "ciphertext c (decimal, optional)")
	flag.Parse()
	if *nStr == "" {
		fmt.Println("usage: -n <n> [-c <c>]")
		return
	}
	initInv()
	tr := loadWords(wordsPath)
	n := parseBig(*nStr)

	pPhrase, qPhrase, ok := solve(n, tr)
	if !ok {
		fmt.Println("no solution")
		return
	}

	p := new(big.Int).SetBytes([]byte(pPhrase))
	q := new(big.Int).SetBytes([]byte(qPhrase))
	c := parseBig(*cStr)
	phi := new(big.Int).Mul(new(big.Int).Sub(p, big.NewInt(1)), new(big.Int).Sub(q, big.NewInt(1)))
	d := new(big.Int).ModInverse(big.NewInt(e), phi)
	m := new(big.Int).Exp(c, d, n)
	fmt.Println("🎉🎉🎉")
	fmt.Println("[+] FLAG: " + string(m.Bytes()))
}
