// Source: https://usaco.guide/general/io

#include <bits/stdc++.h>
using namespace std;

#define nl '\n'
const int N = 1e6+6;
const int m = 1000000007;
int dp[N];
int main() {
    
    memset(dp, 0, sizeof(dp));
    dp[0] = 1;
    int n; cin >> n;

    for(int i = 1;i <= n; ++i){
        for(int j = 0; j < 6; ++j){
            if(j <= i){
                dp[i] = (dp[i] + dp[i-j]) % m;
            }
        }
    }

    cout << dp[n] << nl;


}
