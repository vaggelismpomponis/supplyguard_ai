# Οδηγός Git για το SupplyGuard AI

Remote repository: `https://github.com/vaggelismpomponis/supplyguard_ai.git`

## 1. Βασικές έννοιες

| Έννοια | Περιγραφή |
|--------|-----------|
| Repository (repo) | Ο φάκελος του project μαζί με το ιστορικό αλλαγών |
| Commit | Ένα αποθηκευμένο «στιγμιότυπο» των αλλαγών |
| Branch | Ξεχωριστή γραμμή ανάπτυξης |
| Remote (`origin`) | Το repository στο GitHub |
| Pull Request (PR) | Αίτημα για συγχώνευση ενός branch σε άλλο, με review |

## 2. Αρχική ρύθμιση

```powershell
git config --global user.name "Το Όνομά σου"
git config --global user.email "email@example.com"

# Κλωνοποίηση του repo (αν δεν υπάρχει τοπικά)
git clone https://github.com/vaggelismpomponis/supplyguard_ai.git
cd supplyguard_ai

# Έλεγχος remote
git remote -v
```

## 3. Βασικές εντολές

```powershell
git status                  # Κατάσταση αρχείων
git diff                    # Αλλαγές που δεν έχουν γίνει stage
git add <αρχείο>            # Stage ενός αρχείου
git add .                   # Stage όλων των αλλαγών
git commit -m "Μήνυμα"      # Δημιουργία commit
git log --oneline           # Σύντομο ιστορικό
git log --oneline --graph --all   # Ιστορικό με γράφημα branches
git fetch origin            # Κατεβάζει αλλαγές χωρίς να τις συγχωνεύσει
git pull                    # fetch + merge στο τρέχον branch
git push                    # Ανεβάζει commits στο remote
git switch <branch>         # Μετάβαση σε άλλο branch
```

### Αναίρεση αλλαγών

```powershell
git restore <αρχείο>            # Απόρριψη αλλαγών σε αρχείο (μη αναστρέψιμο)
git restore --staged <αρχείο>   # Αφαίρεση από το stage
git revert <commit-hash>        # Νέο commit που αναιρεί ένα παλιό (ασφαλές)
git stash                       # Προσωρινή αποθήκευση αλλαγών
git stash pop                   # Επαναφορά των stashed αλλαγών
```

> Απόφυγε `git reset --hard` και `git push --force` εκτός αν ξέρεις ακριβώς τι κάνεις.

## 4. Στρατηγική branches

Το project χρησιμοποιεί δύο μόνιμα branches:

- `main`: σταθερός κώδικας, έτοιμος για παράδοση/release.
- `develop`: ο κώδικας ανάπτυξης, όπου συγκεντρώνονται όλα τα features.

Για κάθε νέα εργασία δημιουργείται **feature branch από το `develop`**:

```mermaid
gitGraph
   commit id: "Initial commit"
   branch develop
   checkout develop
   commit id: "develop"
   branch feature/login
   checkout feature/login
   commit id: "feat 1"
   commit id: "feat 2"
   checkout develop
   merge feature/login
   checkout main
   merge develop
```

Συνοπτικά η ροή είναι:

1. Κόβεις το feature branch από το `develop`.
2. Ανοίγεις PR `feature/... → develop`.
3. Ο reviewer κάνει **Merge Squash** στο `develop` (τα commits του feature γίνονται ένα) και διαγράφει το feature branch στο remote.
4. Όταν το `develop` είναι σταθερό, ανοίγεται release PR `develop → main` με **Merge commit**.

Το `git fetch` δεν συγχωνεύει τίποτα, και το `develop` δεν παίρνει αυτόματα αλλαγές από το `main`. Το `main` αλλάζει μόνο από release PR, οπότε κανονικά δεν έχει commits που λείπουν από το `develop`.

### Ονοματολογία branches

| Τύπος | Παράδειγμα |
|-------|------------|
| Νέο feature | `feature/eval-suite-105` |
| Διόρθωση σφάλματος | `bugfix/approval-double-click` |
| Επείγουσα διόρθωση | `hotfix/fix-seed-crash` |
| Τεκμηρίωση | `docs/demo-script-rehearsal` |

Χρησιμοποίησε πεζά γράμματα και παύλες, χωρίς κενά.

## 5. Εργασία με feature branch (βήμα προς βήμα)

### Βήμα 1: Ενημέρωση του `develop`

```powershell
git fetch origin
git checkout develop
git pull origin develop
```

Αν το τοπικό `develop` δεν υπάρχει ακόμα:

```powershell
git checkout -b develop --track origin/develop
```

### Βήμα 2: Δημιουργία feature branch από το `develop`

```powershell
git checkout -b feature/eval-suite-105
```

### Βήμα 3: Δουλειά και commits

```powershell
git status
git add .
git commit -m "feat(eval): add evaluators for the 105 held-out cases"
```

Κάνε μικρά, συχνά commits. Τα μηνύματα ακολουθούν το Conventional Commits (`<type>(<scope>): <subject>`, βλ. [CONTRIBUTING.md](../CONTRIBUTING.md#commit-messages)).

### Βήμα 4: Push του branch στο remote

Την πρώτη φορά:

```powershell
git push -u origin feature/eval-suite-105
```

Στη συνέχεια αρκεί `git push`.

### Βήμα 5: Ενημέρωση με τις τελευταίες αλλαγές του `develop`

Αν το `develop` άλλαξε όσο δούλευες:

```powershell
git fetch origin
git merge origin/develop
# ή, για πιο «καθαρό» ιστορικό:
git rebase origin/develop
```

Αν υπάρχουν conflicts, δες την ενότητα 7.

### Εναλλακτικά: δημιουργία feature branch από το GitHub (web UI)

Μπορείς να δημιουργήσεις το branch από τον browser, χωρίς terminal.

**Μέθοδος Α: από το dropdown των branches**

1. Άνοιξε `https://github.com/vaggelismpomponis/supplyguard_ai`.
2. Στην καρτέλα **Code** άνοιξε το dropdown των branches (πάνω αριστερά, δείχνει π.χ. `main`) και διάλεξε `develop`.
3. Ξανάνοιξε το dropdown και γράψε το όνομα του νέου branch, π.χ. `feature/eval-suite-105`, στο πεδίο **Find or create a branch…**.
4. Πάτησε **Create branch feature/eval-suite-105 from develop**.

**Μέθοδος Β: από τη σελίδα Branches**

1. Στην καρτέλα **Code** πάτησε **Branches** (ή άνοιξε `…/supplyguard_ai/branches`).
2. Πάτησε **New branch**, γράψε το όνομα, διάλεξε **Source:** `develop` και πάτησε **Create new branch**.

Μετά, φέρε το νέο branch στον υπολογιστή σου:

```powershell
git fetch origin
git checkout feature/eval-suite-105
```

> Η ακριβής διατύπωση των κουμπιών μπορεί να διαφέρει ελαφρώς ανάλογα με την έκδοση του GitHub.

## 6. Άνοιγμα Pull Request στο GitHub

1. Κάνε push το feature branch (Βήμα 4). Το GitHub συχνά δείχνει αμέσως μπάρα **Compare & pull request**· μπορείς να την πατήσεις και να πας στο βήμα 4.
2. Άνοιξε το repo στο `https://github.com/vaggelismpomponis/supplyguard_ai`.
3. Πήγαινε στην καρτέλα **Pull requests** και πάτησε **New pull request**.
4. Επίλεξε:
   - **base:** `develop`
   - **compare:** `feature/eval-suite-105`

   Αν τα δύο branches είναι ίδια, εμφανίζεται το μήνυμα «There isn't anything to compare». Χρειάζεται τουλάχιστον ένα commit στο feature branch.
5. Πάτησε **Create pull request** και συμπλήρωσε **τίτλο** (σε μορφή `<type>(<scope>): <subject>`) και **περιγραφή** (τι αλλάζει, γιατί, πώς δοκιμάστηκε). Αν υπάρχει σχετικό issue, γράψε `Closes #12`.
6. Πάτησε ξανά **Create pull request**. Από το πλευρικό πάνελ **Reviewers** πρόσθεσε τον reviewer σύμφωνα με το review rotation του [CONTRIBUTING.md](../CONTRIBUTING.md#pull-requests-and-reviews).

   Το PR εμφανίζεται ως **Open**, με τις καρτέλες **Commits** και **Files changed**.

7. Απάντησε στα σχόλια του review αν υπάρχουν. Νέα commits στο ίδιο branch ενημερώνουν αυτόματα το PR.
8. Μετά την έγκριση, ο **reviewer** κάνει **Merge Squash** (ανάλογα με τη συμφωνία της ομάδας).
9. Η διαγραφή του feature branch στο **remote** γίνεται **μόνο από τον reviewer** (βλ. παρακάτω). Ο δημιουργός του PR διαγράφει μόνο το **τοπικό** branch:

```powershell
git checkout develop
git pull origin develop
git branch -d feature/eval-suite-105   # μόνο τοπικά
git fetch --prune                       # καθαρισμός αναφορών σε remote branches που διαγράφηκαν
```

> Μετά από **Squash** το Git δεν αναγνωρίζει το τοπικό feature branch ως merged και το `git branch -d` μπορεί να αρνηθεί. Αφού επιβεβαιώσεις ότι το PR έγινε merge, χρησιμοποίησε `git branch -D feature/eval-suite-105`.

> Ο δημιουργός του PR **δεν** τρέχει `git push origin --delete ...`.

### Για τον reviewer: merge και διαγραφή remote branch

1. Άνοιξε το PR στο GitHub και έλεγξε τις αλλαγές (καρτέλα **Files changed**).
2. Πάτησε **Review changes**, διάλεξε **Approve** και **Submit review** αν όλα είναι σωστά.
3. Στο κάτω μέρος του PR άνοιξε το βελάκι δίπλα στο κουμπί merge και διάλεξε **Squash and merge** (για PR σε `develop`). Για release PR προς `main` διάλεξε **Create a merge commit**.

   Αν το PR δεν έχει τις απαιτούμενες εγκρίσεις, ένας administrator μπορεί παρ' όλα αυτά να κάνει merge. Χρησιμοποίησέ το μόνο με συμφωνία της ομάδας.

4. Έλεγξε τον τίτλο και την περιγραφή του squash commit (ο τίτλος παίρνει αυτόματα το `(#αριθμός)` του PR) και πάτησε **Confirm squash and merge**.
5. Μετά το merge το PR εμφανίζεται ως **Merged** και υπάρχει κουμπί **Delete branch** μέσα στο PR.

Εναλλακτικά, μέσω terminal:

```powershell
git push origin --delete feature/eval-suite-105
```

Προσοχή: τα `main` και `develop` δεν διαγράφονται ποτέ. Προστατεύονται από **Settings → Branches** (branch protection rules ή rulesets).

### Checklist πριν το PR

- [ ] Το branch βασίζεται στο πρόσφατο `develop`
- [ ] Ο κώδικας τρέχει και τα tests περνούν
- [ ] **Έλεγχος conflicts:** Έχει γίνει έλεγχος με το remote target branch (`git fetch origin` και `git merge-tree --write-tree HEAD origin/develop`) και δεν υπάρχει κανένα conflict
- [ ] Δεν υπάρχουν περιττά αρχεία ή secrets (κωδικοί, tokens)
- [ ] Τα commit messages είναι κατανοητά

### Release: `develop` προς `main`

Όταν το `develop` είναι σταθερό, άνοιξε PR με **base:** `main` και **compare:** `develop`.

Στο release PR χρησιμοποίησε **Merge commit** και όχι Squash. Με Squash το `main` παίρνει ένα νέο commit που δεν υπάρχει στο `develop`, τα δύο branches φαίνονται αποκλίνοντα και το επόμενο release PR μπορεί να δείξει περιττά conflicts.

Αν γίνει αλλαγή απευθείας στο `main` (π.χ. hotfix), φέρε την στο `develop` με PR `main → develop` ή τοπικά:

```powershell
git fetch origin
git checkout develop
git merge origin/main
git push origin develop
```

## 7. Επίλυση conflicts

```powershell
git merge origin/develop
# Git: CONFLICT (content): Merge conflict in <αρχείο>
```

1. Άνοιξε το αρχείο και βρες τους δείκτες:

   ```
   <<<<<<< HEAD
   δική σου έκδοση
   =======
   έκδοση από το develop
   >>>>>>> origin/develop
   ```

2. Κράτησε τον σωστό κώδικα και σβήσε τους δείκτες.
3. Ολοκλήρωσε τη συγχώνευση:

   ```powershell
   git add <αρχείο>
   git commit
   git push
   ```

Για ακύρωση της συγχώνευσης: `git merge --abort`.

## 8. Χρήσιμες εντολές για branches

```powershell
git branch                      # Τοπικά branches
git branch -a                   # Τοπικά και remote branches
git checkout <branch>           # Μετάβαση σε branch
git switch <branch>             # Σύγχρονη εναλλακτική του checkout
git switch -c <νέο-branch>      # Δημιουργία και μετάβαση
git branch -d <branch>          # Διαγραφή τοπικού branch (μετά από merge)
git branch -D <branch>          # Εξαναγκασμένη διαγραφή
git fetch --prune               # Καθαρισμός διαγραμμένων remote branches
```

## 9. Καλές πρακτικές

- Μην κάνεις commit απευθείας στα `main` και `develop`. Χρησιμοποίησε feature branches και PRs.
- Ένα branch αντιστοιχεί σε μία εργασία.
- Κάνε `git pull` πριν ξεκινήσεις δουλειά.
- Γράφε σαφή commit messages, π.χ. «Προσθήκη φόρμας login».
- Μην κάνεις commit αρχεία με κωδικούς ή ευαίσθητα δεδομένα. Χρησιμοποίησε το `.gitignore`.
- Μην ξαναγράφεις ιστορικό (`rebase`, `push --force`) σε branches που μοιράζεσαι με άλλους.

## 10. Γρήγορη αναφορά

```powershell
git checkout develop
git pull origin develop
git checkout -b feature/όνομα
# ... αλλαγές ...
git add .
git commit -m "Μήνυμα"
git push -u origin feature/όνομα
# -> Άνοιγμα PR στο GitHub: feature/όνομα -> develop
```
