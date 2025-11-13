# Copyright 2025 KAS Lab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Re-run the plotting for decreasing membership functions with μ(10) ≈ 0
import numpy as np
import matplotlib.pyplot as plt

xs = np.linspace(0, 15, 400)
x_star = 10.0
targets = [0.05, 0.01]  # small values near zero at x=10

# Exponential decay


def k_from_target_exp_decay(mu_star, x_star):
    return -np.log(mu_star) / x_star


plt.figure()
for mu_star in targets:
    k = k_from_target_exp_decay(mu_star, x_star)
    mu = np.exp(-k * xs)
    plt.plot(xs, mu, label=f"μ(10)≈{mu_star}, k={k:.4f}")
plt.axvline(x_star, linestyle='--', linewidth=1)
plt.title("Exponential decay: μ(x) = e^{-k x}")
plt.xlabel("x")
plt.ylabel("μ(x)")
plt.ylim(-0.05, 1.05)
plt.legend()
plt.grid(True, linestyle=':', linewidth=0.5)
exp_decay_path = "/mnt/data/fuzzy_exp_decay.png"
plt.savefig(exp_decay_path, dpi=160, bbox_inches="tight")
plt.show()

# Rational decay


def a_from_target_rational_decay(mu_star, x_star):
    return (mu_star * x_star) / (1.0 - mu_star)


plt.figure()
for mu_star in targets:
    a = a_from_target_rational_decay(mu_star, x_star)
    mu = a / (xs + a)
    plt.plot(xs, mu, label=f"μ(10)≈{mu_star}, a={a:.4f}")
plt.axvline(x_star, linestyle='--', linewidth=1)
plt.title("Rational decay: μ(x) = a / (x + a)")
plt.xlabel("x")
plt.ylabel("μ(x)")
plt.ylim(-0.05, 1.05)
plt.legend()
plt.grid(True, linestyle=':', linewidth=0.5)
rat_decay_path = "/mnt/data/fuzzy_rational_decay.png"
plt.savefig(rat_decay_path, dpi=160, bbox_inches="tight")
plt.show()

exp_decay_path, rat_decay_path
